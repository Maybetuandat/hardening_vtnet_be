from sqlalchemy.orm import Session
from typing import Optional, List
from dao.workload_dao import WorkLoadDAO
from services.rule_service import RuleService

from models.workload import WorkLoad
from models.rule import Rule

from schemas.workload import (
    WorkLoadCreate, 
    WorkLoadUpdate, 
    WorkLoadResponse, 
    WorkLoadListResponse, 
    WorkLoadSearchParams
)
from schemas.rule import RuleCreate, RuleResponse

import math

class WorkloadService:
    def __init__(self, db: Session):
        self.dao = WorkLoadDAO(db)
        self.db = db
        self.rule_service = RuleService(db)
        
    
    def get_all_workloads(self, page: int = 1, page_size: int = 10) -> WorkLoadListResponse:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100
            
        skip = (page - 1) * page_size
        workloads, total = self.dao.get_workloads_with_pagination(skip=skip, limit=page_size)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        workload_responses = []
        for workload in workloads:
            workload_responses.append(self._convert_to_response(workload))
        
        return WorkLoadListResponse(
            workloads=workload_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def get_workload_name_byid(self, workload_id: int) -> Optional[str]:
        if workload_id <= 0:
            return None
        workload = self.dao.get_by_id(workload_id)
        print(f"Workload ID: {workload_id}, Name: {workload.name if workload else 'Not found'}")
        if workload:
            return workload.name
        return None

    def get_workload_by_id(self, workload_id: int) -> Optional[WorkLoadResponse]:
        if workload_id <= 0:
            return None
        workload = self.dao.get_by_id(workload_id)
        if workload:
            return self._convert_to_response(workload)
        return None
    
    def search_workloads(self, search_params: WorkLoadSearchParams) -> WorkLoadListResponse:
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.page_size))
            
        skip = (page - 1) * page_size
        workloads, total = self.dao.search_workloads(
            keyword=search_params.keyword,
            skip=skip,
            limit=page_size
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        workload_responses = []
        for workload in workloads:
            workload_responses.append(self._convert_to_response(workload))
        
        return WorkLoadListResponse(
            workloads=workload_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    def create_workload(self, workload_data: WorkLoadCreate) -> WorkLoadResponse:
        try:
            self._validate_workload_create_data(workload_data)
            
            # Kiểm tra name đã tồn tại chưa
            if self.dao.check_name_exists(workload_data.name):
                raise ValueError(f"Workload với tên '{workload_data.name}' đã tồn tại")
            
            workload_dict = workload_data.dict()
            workload_model = WorkLoad(**workload_dict)
            
            created_workload = self.dao.create(workload_model)
            return self._convert_to_response(created_workload)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi tạo workload: {str(e)}")
    
    def create_workload_with_rules_and_commands(
        self, 
        workload_data: WorkLoadCreate, 
        rules_data: List[RuleCreate], 
        
    ) -> dict:
        """
        Tạo workload cùng với danh sách rules và commands
        Rollback nếu bất kỳ thao tác nào thất bại
        """
        # Sử dụng try/except để đảm bảo transaction rollback
        try:
            # 1. Tạo workload
            self._validate_workload_create_data(workload_data)
            
            if self.dao.check_name_exists(workload_data.name):
                raise ValueError(f"Workload với tên '{workload_data.name}' đã tồn tại")
            
            workload_dict = workload_data.dict()
            workload_model = WorkLoad(**workload_dict)
            
            # Thêm vào session nhưng chưa commit
            self.db.add(workload_model)
            self.db.flush()  # Để lấy ID nhưng chưa commit
            
            # 2. Tạo rules và gán workload_id
            created_rules = []
            for rule_data in rules_data:
                # Gán workload_id cho rule
                rule_data.workload_id = workload_model.id
                
                # Tạo rule model
                rule_dict = rule_data.dict()
                rule_model = Rule(**rule_dict)
                self.db.add(rule_model)
                self.db.flush()  # Để lấy ID
                
                # Convert to response
                rule_response = RuleResponse(
                    id=rule_model.id,
                    name=rule_model.name,
                    description=rule_model.description,
                    
                    workload_id=rule_model.workload_id,
                    parameters=rule_model.parameters,
                    is_active=rule_model.is_active,
                    created_at=rule_model.created_at,
                    updated_at=rule_model.updated_at
                )
                created_rules.append(rule_response)
            
          
            
            # Commit tất cả changes
            self.db.commit()
            
            return {
                "workload": self._convert_to_response(workload_model),
                "rules": created_rules,
                
                "message": "Tạo workload với rules và commands thành công"
            }
            
        except Exception as e:
            # Rollback transaction nếu có lỗi
            self.db.rollback()
            raise Exception(f"Lỗi khi tạo workload với rules và commands: {str(e)}")
    
    def update_workload(self, workload_id: int, workload_data: WorkLoadUpdate) -> Optional[WorkLoadResponse]:
        try:
            if workload_id <= 0:
                return None
                
            existing_workload = self.dao.get_by_id(workload_id)
            if not existing_workload:
                return None
                
            self._validate_workload_update_data(workload_data)
            
            # Kiểm tra name đã tồn tại chưa (trừ chính nó)
            if workload_data.name and workload_data.name != existing_workload.name:
                if self.dao.check_name_exists(workload_data.name):
                    raise ValueError(f"Workload với tên '{workload_data.name}' đã tồn tại")
            
            update_data = workload_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(existing_workload, field) and value is not None:
                    setattr(existing_workload, field, value)
            
            updated_workload = self.dao.update(existing_workload)
            return self._convert_to_response(updated_workload)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi cập nhật workload: {str(e)}")
    
    def delete_workload(self, workload_id: int) -> bool:
        try:
            if workload_id <= 0:
                return False
                
            existing_workload = self.dao.get_by_id(workload_id)
            if not existing_workload:
                return False
            
            self.dao.delete(existing_workload)
            return True
            
        except Exception as e:
            raise Exception(f"Lỗi khi xóa workload: {str(e)}")
    
    def _convert_to_response(self, workload: WorkLoad) -> WorkLoadResponse:
        return WorkLoadResponse(
            id=workload.id,
            name=workload.name,
            description=workload.description,
            created_at=workload.created_at,
            updated_at=workload.updated_at
        )
    
    def _validate_workload_create_data(self, workload_data: WorkLoadCreate) -> None:
        if not workload_data.name or not workload_data.name.strip():
            raise ValueError("Tên workload không được để trống")
    
    def _validate_workload_update_data(self, workload_data: WorkLoadUpdate) -> None:
        if workload_data.name is not None and (not workload_data.name or not workload_data.name.strip()):
            raise ValueError("Tên workload không được để trống")
      
   
            
    def get_workload_id_by_name(self, name: str) -> Optional[int]:
        """
        Lấy workload ID từ name để sử dụng khi upload server
        """
        try:
            if not name or not name.strip():
                return None
                
            workload = self.dao.get_by_name(name.strip())
            return workload.id if workload else None
        except Exception as e:
            raise Exception(f"Lỗi khi lấy workload ID từ name: {str(e)}")
    def check_workload_name_exists(self, name: str) -> bool:
        try:
            if not name or not name.strip():
                return False
            return self.dao.check_name_exists(name.strip())
        except Exception as e:
            raise Exception(f"Lỗi khi kiểm tra tên workload: {str(e)}")
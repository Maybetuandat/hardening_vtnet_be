from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
import json
import math

from dao.role_dao import RoleDAO
from models.role import Role
from schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, 
    RoleListResponse, RoleSearchParams
)

class RoleService:
    def __init__(self, db: Session):
        self.db = db
        self.dao = RoleDAO(db)
    
    def get_all_roles(self) -> List[RoleResponse]:
        roles = self.dao.get_all()
        return [self._convert_to_response(role) for role in roles]
    
    def get_role_by_id(self, role_id: int) -> Optional[RoleResponse]:
        if role_id <= 0:
            return None
        
        role = self.dao.get_by_id(role_id)
        if role:
            return self._convert_to_response(role)
        return None
    
    def get_role_by_name(self, name: str) -> Optional[RoleResponse]:
        role = self.dao.get_by_name(name)
        if role:
            return self._convert_to_response(role)
        return None
    
    def search_roles(self, search_params: RoleSearchParams) -> RoleListResponse:
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.page_size))
        
        skip = (page - 1) * page_size
        
        roles, total = self.dao.search_roles(
            keyword=search_params.keyword,
            skip=skip,
            limit=page_size
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        role_responses = [self._convert_to_response(role) for role in roles]
        
        return RoleListResponse(
            roles=role_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    def create_role(self, role_data: RoleCreate) -> RoleResponse:
        try:
            self._validate_role_create_data(role_data)
            
            if self.dao.check_name_exists(role_data.name):
                raise ValueError(f"Role với tên '{role_data.name}' đã tồn tại")
            
            # Validate permissions JSON if provided
            if role_data.permissions:
                try:
                    json.loads(role_data.permissions)
                except json.JSONDecodeError:
                    raise ValueError("Permissions phải là JSON hợp lệ")
            
            role_dict = role_data.dict()
            role_model = Role(**role_dict)
            
            created_role = self.dao.create(role_model)
            self.db.commit()
            
            return self._convert_to_response(created_role)
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def update_role(self, role_id: int, role_data: RoleUpdate) -> Optional[RoleResponse]:
        try:
            if role_id <= 0:
                return None
            
            existing_role = self.dao.get_by_id(role_id)
            if not existing_role:
                return None
            
            # Check if new name already exists
            if role_data.name and self.dao.check_name_exists(role_data.name, exclude_id=role_id):
                raise ValueError(f"Role với tên '{role_data.name}' đã tồn tại")
            
            # Validate permissions JSON if provided
            if role_data.permissions:
                try:
                    json.loads(role_data.permissions)
                except json.JSONDecodeError:
                    raise ValueError("Permissions phải là JSON hợp lệ")
            
            # Update fields
            for field, value in role_data.dict(exclude_unset=True).items():
                setattr(existing_role, field, value)
            
            updated_role = self.dao.update(existing_role)
            self.db.commit()
            
            return self._convert_to_response(updated_role)
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def delete_role(self, role_id: int) -> bool:
        try:
            if role_id <= 0:
                return False
            
            # Check if role has users
            role = self.dao.get_by_id(role_id)
            if not role:
                return False
            
            if role.users:
                raise ValueError("Không thể xóa role đang được sử dụng bởi user")
            
            success = self.dao.delete(role_id)
            if success:
                self.db.commit()
            
            return success
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def get_role_permissions(self, role_id: int) -> List[str]:
        """Lấy danh sách permissions của role"""
        role = self.dao.get_by_id(role_id)
        if not role or not role.permissions:
            return []
        
        try:
            permissions = json.loads(role.permissions)
            return permissions if isinstance(permissions, list) else []
        except json.JSONDecodeError:
            return []
    
    def _validate_role_create_data(self, role_data: RoleCreate):
        if not role_data.name or not role_data.name.strip():
            raise ValueError("Tên role không được để trống")
        
        if len(role_data.name.strip()) > 50:
            raise ValueError("Tên role không được vượt quá 50 ký tự")
    
    def _convert_to_response(self, role: Role) -> RoleResponse:
        return RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=role.permissions,
            created_at=role.created_at,
            updated_at=role.updated_at
        )
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.config_database import get_db

from services.workload_service import WorkloadService
from schemas.workload import (
    WorkLoadCreate, 
    WorkLoadUpdate, 
    WorkLoadResponse, 
    WorkLoadListResponse, 
    WorkLoadSearchParams,
    WorkloadWithRulesAndCommandsRequest
)
from schemas.rule import RuleCreate
from schemas.command import CommandCreate
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/api/workloads", tags=["Workloads"])



@router.get("/", response_model=WorkLoadListResponse)
async def get_workloads(
    keyword: str = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách workloads với phân trang và tìm kiếm
    - Nếu keyword rỗng: lấy tất cả workloads với phân trang
    - Nếu có keyword: tìm kiếm theo tên workload
    """
    try:
        workload_service = WorkloadService(db)
        
        # Tạo search params
        search_params = WorkLoadSearchParams(
            keyword=keyword,
            page=page,
            page_size=page_size
        )
        
        return workload_service.search_workloads(search_params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy danh sách workloads: {str(e)}"
        )

@router.get("/{workload_id}", response_model=WorkLoadResponse)
async def get_workload_by_id(
    workload_id: int,
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin workload theo ID
    """
    try:
        workload_service = WorkloadService(db)
        workload = workload_service.get_workload_by_id(workload_id)
        if not workload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy workload với ID: {workload_id}"
            )
        return workload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy thông tin workload: {str(e)}"
        )

@router.post("/", response_model=WorkLoadResponse)
async def create_workload(
    workload_data: WorkLoadCreate,
    db: Session = Depends(get_db)
):
    """
    Tạo workload mới
    """
    try:
        workload_service = WorkloadService(db)
        return workload_service.create_workload(workload_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo workload: {str(e)}"
        )

@router.post("/create-with-rules-commands")
async def create_workload_with_rules_and_commands(
    request: WorkloadWithRulesAndCommandsRequest,
    db: Session = Depends(get_db)
):
    """
    Tạo workload cùng với rules và commands
    Thực hiện rollback nếu có lỗi xảy ra trong quá trình tạo
    
    Lưu ý:
    - workload_id sẽ được gán tự động cho các rules
    - rule_id sẽ được gán tự động cho các commands dựa trên rule_index
    - rule_index là chỉ số của rule trong danh sách rules (bắt đầu từ 0)
    """
    try:
        workload_service = WorkloadService(db)
        
        # Convert WorkloadRuleCreate thành RuleCreate
        rules_data = []
        for rule in request.rules:
            rule_create = RuleCreate(
                name=rule.name,
                description=rule.description,
                severity=rule.severity,
                workload_id=0,  # Sẽ được gán lại trong service
                parameters=rule.parameters,
                is_active=rule.is_active
            )
            rules_data.append(rule_create)
        
        # Convert WorkloadCommandCreate thành CommandCreate
        commands_data = []
        for command in request.commands:
            command_create = CommandCreate(
                rule_id=0,  # Sẽ được gán lại trong service
                rule_index=command.rule_index,
                os_version=command.os_version,
                command_text=command.command_text,
                is_active=command.is_active
            )
            commands_data.append(command_create)
        
        result = workload_service.create_workload_with_rules_and_commands(
            workload_data=request.workload,
            rules_data=rules_data,
            commands_data=commands_data
        )
        return {
            "success": True,
            "data": result,
            "message": "Tạo workload với rules và commands thành công"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo workload với rules và commands: {str(e)}"
        )

@router.put("/{workload_id}", response_model=WorkLoadResponse)
async def update_workload(
    workload_id: int,
    workload_data: WorkLoadUpdate,
    db: Session = Depends(get_db)
):
    """
    Cập nhật thông tin workload
    """
    try:
        workload_service = WorkloadService(db)
        updated_workload = workload_service.update_workload(workload_id, workload_data)
        if not updated_workload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy workload với ID: {workload_id}"
            )
        return updated_workload
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi cập nhật workload: {str(e)}"
        )

@router.delete("/{workload_id}")
async def delete_workload(
    workload_id: int,
    db: Session = Depends(get_db)
):
    """
    Xóa workload
    """
    try:
        workload_service = WorkloadService(db)
        success = workload_service.delete_workload(workload_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy workload với ID: {workload_id}"
            )
        return {
            "success": True,
            "message": f"Xóa workload ID {workload_id} thành công"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xóa workload: {str(e)}"
        )


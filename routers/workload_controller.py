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
    WorkloadWithRulesRequest,
    
)
from utils.auth import require_admin, require_user





router = APIRouter(prefix="/api/workloads", tags=["Workloads"])



@router.get("/", response_model=WorkLoadListResponse)
async def get_workloads(
    keyword: str = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db), 
    current_user = Depends(require_user())
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
            detail=f"Error fetching workloads: {str(e)}"
        )

@router.get("/{workload_id}", response_model=WorkLoadResponse)
async def get_workload_by_id(
    workload_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_user())
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
                detail=f"Workload not found: {workload_id}"
            )
        return workload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching workload information: {str(e)}"
        )

@router.post("/", response_model=WorkLoadResponse)
async def create_workload(
    workload_data: WorkLoadCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin())
):
    """
    Tạo workload mới
    """
    try:
        workload_service = WorkloadService(db)
        return workload_service.create(workload_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating workload: {str(e)}"
        )

@router.post("/create-with-rules-commands")
async def create_workload_with_rules_and_commands(
    request: WorkloadWithRulesRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin())
):
   
    try:
        workload_service = WorkloadService(db)
        
        
       
        
        result = workload_service.create_workload_with_rules_and_commands(
            workload_data=request.workload,
            rules_data=request.rules,
            
        )
        return {
            "success": True,
            "data": result,
            "message": "Create workload with rules and commands successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating workload with rules and commands: {str(e)}"
        )

@router.put("/{workload_id}", response_model=WorkLoadResponse)
async def update_workload(
    workload_id: int,
    workload_data: WorkLoadUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin())
):
    """
    Cập nhật thông tin workload
    """
    try:
        workload_service = WorkloadService(db)
        updated_workload = workload_service.update(workload_id, workload_data)
        if not updated_workload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workload not found: {workload_id}"
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
            detail=f"Error updating workload: {str(e)}"
        )

@router.delete("/{workload_id}")
async def delete_workload(
    workload_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin())
):
    """
    Xóa workload
    """
    try:
        workload_service = WorkloadService(db)
        success = workload_service.delete(workload_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workload not found: {workload_id}"
            )
        return {
            "success": True,
            "message": f"Delete workload ID {workload_id} successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting workload: {str(e)}"
        )

@router.post("/validate/workload-name/{workload_name}")
async def validate_workload_name(
       workload_name: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin())
):
    """
    Kiểm tra tên workload đã tồn tại hay chưa
    """
    try:
        workload_service = WorkloadService(db)
        exists = workload_service.check_workload_name_exists(workload_name)
        return {
            "exists": exists,
            "message": "Workload name already exists" if exists else "Valid workload name"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking workload name: {str(e)}"
        )
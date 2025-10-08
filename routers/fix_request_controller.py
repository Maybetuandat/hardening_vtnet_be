# routers/fix_request_controller.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from config.config_database import get_db
from schemas.fix_request import FixRequestApprove, FixRequestCreate, FixRequestListResponse, FixRequestResponse
from utils.auth import require_user, require_admin

from schemas.common import SuccessResponse
from services.fix_request_service import FixRequestService

router = APIRouter(prefix="/api/fix-requests", tags=["Fix Requests"])


@router.post("/", response_model=FixRequestResponse)
async def create_fix_request(
    data: FixRequestCreate,
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """
    Tạo fix request mới
    """
    try:
        service = FixRequestService(db)
        return service.create_fix_request(data, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=FixRequestListResponse)
async def get_all_fix_requests(
    status: Optional[str] = Query(None, regex="^(pending|approved|rejected|executing|completed|failed)$"),
    current_user=Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Lấy tất cả fix requests (chỉ admin)
    """
    try:
        service = FixRequestService(db)
        requests = service.get_all_requests(status)
        return FixRequestListResponse(requests=requests, total=len(requests))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-requests", response_model=FixRequestListResponse)
async def get_my_fix_requests(
    status: Optional[str] = Query(None),
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """
    Lấy fix requests của user hiện tại
    """
    try:
        service = FixRequestService(db)
        requests = service.get_user_requests(current_user, status)
        return FixRequestListResponse(requests=requests, total=len(requests))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{request_id}", response_model=FixRequestResponse)
async def get_fix_request_detail(
    request_id: int,
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """
    Lấy chi tiết fix request
    """
    try:
        service = FixRequestService(db)
        request = service.get_request_by_id(request_id)
        
        if not request:
            raise HTTPException(status_code=404, detail="Fix request not found")
        
        # Kiểm tra quyền: admin hoặc người tạo request
        if current_user.role != 'admin' and request.created_by != current_user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return request
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{request_id}/approve", response_model=FixRequestResponse)
async def approve_fix_request(
    request_id: int,
    data: FixRequestApprove,
    current_user=Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Admin approve fix request
    """
    try:
        service = FixRequestService(db)
        return service.approve_request(
            request_id=request_id,
            admin_user=current_user,
            admin_comment=data.admin_comment
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{request_id}/reject", response_model=FixRequestResponse)
async def reject_fix_request(
    request_id: int,
    data: FixRequestApprove,
    current_user=Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Admin reject fix request
    """
    try:
        service = FixRequestService(db)
        return service.reject_request(
            request_id=request_id,
            admin_user=current_user,
            admin_comment=data.admin_comment
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{request_id}", response_model=SuccessResponse)
async def delete_fix_request(
    request_id: int,
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """
    Xóa fix request (người tạo hoặc admin)
    """
    try:
        service = FixRequestService(db)
        service.delete_request(request_id, current_user)
        return SuccessResponse(message="Fix request deleted successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
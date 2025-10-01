# routers/rule_change_request_controller.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from utils.auth import require_user, require_admin
from schemas.rule_change_request import (
    RuleChangeRequestCreate,
    RuleChangeRequestCreateNew,
    RuleChangeRequestUpdate,
    RuleChangeRequestResponse,
    RuleChangeRequestListResponse
)
from schemas.common import SuccessResponse
from services.rule_change_request_service import RuleChangeRequestService

router = APIRouter(prefix="/api/rule-change-requests", tags=["Rule Change Requests"])

# ===== USER ENDPOINTS =====

@router.post("/update", response_model=RuleChangeRequestResponse)
async def create_update_request(
    data: RuleChangeRequestCreate,
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """User tạo request UPDATE rule"""
    try:
        service = RuleChangeRequestService(db)
        return service.create_update_request(
            rule_id=data.rule_id,
            new_rule_data=data.new_value,
            current_user=current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=RuleChangeRequestResponse)
async def create_new_rule_request(
    data: RuleChangeRequestCreateNew,
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """User tạo request CREATE rule mới"""
    try:
        service = RuleChangeRequestService(db)
        new_rule_data = {
            "name": data.name,
            "description": data.description,
            "command": data.command,
            "parameters": data.parameters,
            "suggested_fix": data.suggested_fix,
            "is_active": data.is_active
        }
        return service.create_new_rule_request(
            workload_id=data.workload_id,
            new_rule_data=new_rule_data,
            current_user=current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-requests", response_model=RuleChangeRequestListResponse)
async def get_my_requests(
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """User xem lịch sử requests của mình"""
    try:
        service = RuleChangeRequestService(db)
        requests = service.get_user_requests(current_user.id)
        return RuleChangeRequestListResponse(requests=requests, total=len(requests))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== ADMIN ENDPOINTS =====

@router.get("/pending", response_model=RuleChangeRequestListResponse)
async def get_pending_requests(
    current_user=Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Admin lấy tất cả pending requests"""
    try:
        service = RuleChangeRequestService(db)
        requests = service.get_all_pending_requests()
        return RuleChangeRequestListResponse(requests=requests, total=len(requests))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{request_id}", response_model=RuleChangeRequestResponse)
async def get_request_detail(
    request_id: int,
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """Lấy chi tiết 1 request"""
    try:
        service = RuleChangeRequestService(db)
        request = service.get_request_by_id(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Check permission: admin or owner
        if current_user.role != 'admin' and request.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return request
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{request_id}/approve", response_model=RuleChangeRequestResponse)
async def approve_request(
    request_id: int,
    data: RuleChangeRequestUpdate,
    current_user=Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Admin approve request"""
    try:
        service = RuleChangeRequestService(db)
        return service.approve_request(
            request_id=request_id,
            admin_user=current_user,
            admin_note=data.admin_note
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{request_id}/reject", response_model=RuleChangeRequestResponse)
async def reject_request(
    request_id: int,
    data: RuleChangeRequestUpdate,
    current_user=Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Admin reject request"""
    try:
        service = RuleChangeRequestService(db)
        return service.reject_request(
            request_id=request_id,
            admin_user=current_user,
            admin_note=data.admin_note
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workload/{workload_id}", response_model=RuleChangeRequestListResponse)
async def get_workload_requests(
    workload_id: int,
    status: Optional[str] = Query(None, regex="^(pending|approved|rejected)$"),
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """Lấy requests theo workload"""
    try:
        service = RuleChangeRequestService(db)
        requests = service.get_workload_requests(workload_id, status)
        return RuleChangeRequestListResponse(requests=requests, total=len(requests))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
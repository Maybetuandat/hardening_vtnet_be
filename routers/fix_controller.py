# routers/fix_controller.py (Updated với request utils)
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.fix_execution import ServerFixRequest, ServerFixResponse
from services.fix_service import FixService
from services.fix_action_log_service import FixActionLogService
from utils.auth import require_admin, require_user
from utils.request_utils import get_client_ip, get_user_agent

router = APIRouter(prefix="/api/fixes", tags=["Fix"])

def create_fix_service(
    request: Request,
    current_user = Depends(require_user()),
    db: Session = Depends(get_db)
):
    
    return FixService(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

def get_fix_log_service(db: Session = Depends(get_db)) -> FixActionLogService:
    """Get FixActionLogService instance"""
    return FixActionLogService(db)

@router.post("/server", response_model=ServerFixResponse)
def execute_server_fixes(
    fix_request: ServerFixRequest,
    fix_service: FixService = Depends(create_fix_service),
    current_user = Depends(require_user())
):
    try:
        if not fix_request.rule_result_ids:
            raise HTTPException(
                status_code=400, 
                detail="rule_result_ids list cannot be empty"
            )
        
        return fix_service.execute_server_fixes(fix_request, current_user)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing server fixes: {str(e)}")

@router.get("/logs")
def get_fix_logs(
    compliance_id: int = None,
    rule_result_id: int = None,
    user_id: int = None,
    keyword: str = None,
    page: int = 1,
    page_size: int = 20,
    fix_log_service: FixActionLogService = Depends(get_fix_log_service),
    current_user = Depends(require_user())
):
  
    try:
        if compliance_id:
            return fix_log_service.get_fix_logs_by_compliance(compliance_id, page, page_size)
        elif rule_result_id:
            return fix_log_service.get_fix_logs_by_rule_result(rule_result_id, page, page_size)
        elif user_id:
            return fix_log_service.get_fix_logs_by_user(user_id, page, page_size)
        else:
            return fix_log_service.search_fix_logs(keyword=keyword, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/recent")
def get_recent_fix_logs(
    hours: int = 24,
    page: int = 1,
    page_size: int = 20,
    fix_log_service: FixActionLogService = Depends(get_fix_log_service),
    current_user = Depends(require_user())
):
   
    try:
        if hours < 1 or hours > 168:  
            hours = 24
        return fix_log_service.get_recent_fix_logs(hours, page, page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/failed")
def get_failed_fix_logs(
    page: int = 1,
    page_size: int = 20,
    fix_log_service: FixActionLogService = Depends(get_fix_log_service),
    current_user = Depends(require_user())
):
   
    try:
        return fix_log_service.get_failed_fix_logs(page, page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/search")
def search_fix_logs(
    keyword: str = None,
    user_id: int = None,
    compliance_id: int = None,
    rule_result_id: int = None,
    old_status: str = None,
    new_status: str = None,
    is_success: bool = None,
    page: int = 1,
    page_size: int = 20,
    fix_log_service: FixActionLogService = Depends(get_fix_log_service),
    current_user = Depends(require_user())
):
    
    try:
        return fix_log_service.search_fix_logs(
            keyword=keyword,
            user_id=user_id,
            compliance_id=compliance_id,
            rule_result_id=rule_result_id,
            old_status=old_status,
            new_status=new_status,
            is_success=is_success,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
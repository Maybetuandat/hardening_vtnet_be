from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.fix_execution import ServerFixRequest, ServerFixResponse
from services.fix_service import FixService
from utils.auth import require_user


router = APIRouter(prefix="/api/fixes", tags=["Fix Execution"])


def get_fix_service(db: Session = Depends(get_db)) -> FixService:
    return FixService(db)


@router.post("/server", response_model=ServerFixResponse)
def execute_server_fixes(
    request: ServerFixRequest,
    fix_service: FixService = Depends(get_fix_service),
    current_user = Depends(require_user())
):
    try:
        if not request.rule_result_ids:
            raise HTTPException(
                status_code=400, 
                detail="rule_result_ids list cannot be empty"
            )
        
        return fix_service.execute_server_fixes(request)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing server fixes: {str(e)}")


from fastapi import APIRouter
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config.config_database import get_db
from models.rule_result import RuleResult
from schemas.rule import RuleResponse
from schemas.rule_result import RuleResultListResponse, RuleResultResponse
from services.rule_result_service import RuleResultService
from services.compilance_result_service import ComplianceResultService
from utils.auth import require_admin, require_user
router = APIRouter(prefix="/api/rule-results", tags=["Rule Results"])

def get_rule_result_service(db: Session = Depends(get_db)) -> RuleResultService:
    return RuleResultService(db)
def get_compliance_service(db: Session = Depends(get_db)):
    return ComplianceResultService(db)
    
    
@router.get("/", response_model=RuleResultListResponse)
async def get_rule_results_by_compliance(
    compliance_id: int = Query(..., description="ID của Compliance Result"),
    keyword: Optional[str] = Query(None, description="Từ khóa tìm kiếm (để trống để lấy tất cả)"),
    status: Optional[str] = Query(None, description="Trạng thái của Rule Result"),
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng item mỗi trang"),
    rule_result_service: RuleResultService = Depends(get_rule_result_service),
    current_user = Depends(require_user())
) -> RuleResultListResponse:
    try:
        return rule_result_service.get_rule_results_by_compliance_id(compliance_id, keyword=keyword, status=status, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.put("/{rule_result_id}/status", response_model=RuleResultResponse)
async def update_rule_result_status(
    rule_result_id: int,
    new_status: str = Query(..., description="Trạng thái mới của Rule Result"),
    rule_result_service: RuleResultService = Depends(get_rule_result_service),
    compliance_service: ComplianceResultService = Depends(get_compliance_service),
    current_user = Depends(require_admin())
) -> RuleResultResponse:
    try:
        updated_rule_result = rule_result_service.update_rule_result_status(rule_result_id, new_status)
        if not updated_rule_result:
            raise HTTPException(status_code=404, detail="Rule Result not found")
        compliance_service.calculate_score(updated_rule_result.compliance_result_id)
        return updated_rule_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

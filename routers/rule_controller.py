from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from config.config_database import get_db
from schemas.rule import RuleCreate, RuleListResponse, RuleResponse, RuleSearchParams
from services.rule_service import RuleService

router = APIRouter(prefix="/api/rules", tags=["Rules"])

def get_rule_service(db : Session = Depends(get_db)) -> RuleService:
    return RuleService(db)
    
@router.get("/", response_model = RuleListResponse)
async def get_rules(
        keyword: Optional[str] = Query(None, description="Từ khóa tìm kiếm (để trống để lấy tất cả)"),
        page: int = Query(1, ge=1, description="Số trang"),
        page_size: int = Query(10, ge=1, le=100, description="Số lượng item mỗi trang"),
        workload_id: Optional[int] = Query(None, description="ID workload"),
        rule_service: RuleService = Depends(get_rule_service)
        ) -> List[RuleResponse]:

    try:
    
        search_params = RuleSearchParams(
            keyword=keyword,
            page=page,
            size=page_size,
            workload_id=workload_id
         )
        return rule_service.search_rules(search_params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule_by_id(rule_id: int, rule_service: RuleService = Depends(get_rule_service)) -> RuleResponse:
    try:
        rule = rule_service.get_rule_by_id(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule không tìm thấy")
        return rule
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/", response_model=RuleResponse)
async def create_rule(rule: RuleCreate, rule_service: RuleService = Depends(get_rule_service)) -> RuleResponse:
    try:
        return rule_service.create_rule(rule)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: int, rule: RuleCreate, rule_service: RuleService = Depends(get_rule_service)) -> RuleResponse:
    try:
        updated_rule = rule_service.update_rule(rule_id, rule)
        if not updated_rule:
            raise HTTPException(status_code=404, detail="Rule không tìm thấy")
        return updated_rule
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.delete("/{rule_id}", response_model=dict)
async def delete_rule(rule_id: int, rule_service: RuleService = Depends(get_rule_service)) -> dict:
    try:
        rule_service.delete_rule(rule_id)
        return {
            "success": True,
            "message": "Rule deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
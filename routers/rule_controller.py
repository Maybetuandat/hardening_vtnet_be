from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from config.config_database import get_db
from schemas.rule import RuleCheckResult, RuleCreate, RuleExistenceCheckRequest, RuleListResponse, RuleResponse, RuleSearchParams, RuleUpdate
from services.rule_service import RuleService
from utils.auth import require_admin, require_user

router = APIRouter(prefix="/api/rules", tags=["Rules"])

def get_rule_service(db : Session = Depends(get_db)) -> RuleService:
    return RuleService(db)
    
@router.get("/", response_model = RuleListResponse)
async def get_rules(
        keyword: Optional[str] = Query(None, description="keyword to search in rule names"),
        page: int = Query(1, ge=1, description="page number"),
        page_size: int = Query(10, ge=1, le=100, description="page size"),
        workload_id: Optional[int] = Query(None, description="ID workload"),
        rule_service: RuleService = Depends(get_rule_service),
        current_user = Depends(require_user())
        ) -> List[RuleResponse]:

    try:
    
        search_params = RuleSearchParams(
            keyword=keyword,
            page=page,
            page_size=page_size,
            workload_id=workload_id
         )
        print("Debug search params:", search_params)
        return rule_service.search_rules(search_params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule_by_id(
        rule_id: int, 
        rule_service: RuleService = Depends(get_rule_service),
        current_user = Depends(require_user())
) -> RuleResponse:
    try:
        rule = rule_service.get_rule_by_id(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        return rule
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/", response_model=RuleResponse)
async def create_rule(
        rule: RuleCreate, 
        rule_service: RuleService = Depends(get_rule_service),
        current_user = Depends(require_admin())
) -> RuleResponse:
    try:
        return rule_service.create(rule)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/bulk", response_model=List[RuleResponse])
async def create_rules_bulk(
    rules: List[RuleCreate], rule_service: RuleService = Depends(get_rule_service),
    current_user = Depends(require_admin())
) -> List[RuleResponse]:
    try:
        return rule_service.create_bulk(rules)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int, rule: RuleUpdate, rule_service: RuleService = Depends(get_rule_service),
    current_user = Depends(require_user())) -> RuleResponse:
    if current_user.role == 'admin':
        try:
            updated_rule = rule_service.update_with_role_admin(rule_id, rule)
            if not updated_rule:
                raise HTTPException(status_code=404, detail="Rule not found")
            return updated_rule
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        try:
           update_rule = rule_service.update_with_role_user(rule_id, rule)
           if not update_rule:
               raise HTTPException(status_code=404, detail="You don't have permission for update this rule")
           return update_rule
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
@router.delete("/{rule_id}", response_model=dict)
async def delete_rule(
    rule_id: int, rule_service: RuleService = Depends(get_rule_service),
    current_user = Depends(require_admin())
) -> dict:
    try:
        rule_service.delete(rule_id)
        return {
            "success": True,
            "message": "Rule deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/check-existence", response_model=List[RuleCheckResult])
async def check_rules_existence(
   request: RuleExistenceCheckRequest,
    rule_service: RuleService = Depends(get_rule_service),
    current_user = Depends(require_admin())
) -> List[RuleCheckResult]:
    try:
        results = rule_service.check_rules_existence_in_workload(request.workload_id, request.rules)
        return results
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
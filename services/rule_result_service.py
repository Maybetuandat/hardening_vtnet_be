from typing import List, Optional
from dao.rule_result_dao import RuleResultDAO
from sqlalchemy.orm import Session

from models.rule_result import RuleResult
from schemas.rule_result import RuleResultListResponse, RuleResultResponse


class RuleResultService:
    def __init__(self, db: Session):
        self.db = db
        self.dao = RuleResultDAO(db)
        
    
    def get_rule_results_by_compliance_id(
            self, 
            compliance_id: int,                              
            keyword: Optional[str] = None,
            status: Optional[str] = None,                    
            page: int = 1, page_size: int = 10) -> RuleResultListResponse:
        skip = (page - 1) * page_size
        total = self.dao.count_by_compliance_id(compliance_id)
        paginated_results = self.dao.get_by_compliance_id(compliance_id, skip=skip, limit=page_size, keyword=keyword, status=status)

        return RuleResultListResponse(
            total_rule_result=total,
            items=[RuleResultResponse.model_validate(result) for result in paginated_results],
            page=page,
            size=page_size,
            total_pages=(total // page_size) + (1 if total % page_size > 0 else 0)
        )   
    def count_passed_rules(self, compliance_id: int) -> int:
        return self.dao.count_passed_rules(compliance_id)
    
    def count_rules_by_compliance(self, compliance_id: int) -> int:
        return self.dao.count_by_compliance_id(compliance_id)
    def update_rule_result_status(
        self, rule_result_id: int, new_status: str
    ) -> Optional[RuleResultResponse]:
        

        rule_result = self.dao.get_by_id(rule_result_id)
        if not rule_result:
            return None
        rule_result.status = new_status
        updated = self.dao.update(rule_result)
        if not updated:
            return None
        
        return RuleResultResponse.model_validate(updated)
    def create_bulk(self, rule_results: List[RuleResult]) -> List[RuleResult]:
        return self.dao.create_bulk(rule_results)
from typing import List, Optional
from dao.rule_result_dao import RuleResultDAO
from sqlalchemy.orm import Session
import math

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
            page: int = 1, 
            page_size: int = 10) -> RuleResultListResponse:
        
        # Validate parameters
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        skip = (page - 1) * page_size
        
        # Get filtered count and data
        total = self.dao.count_filtered(compliance_id, keyword=keyword, status=status)
        paginated_results = self.dao.get_by_compliance_id(
            compliance_id, 
            skip=skip, 
            limit=page_size, 
            keyword=keyword, 
            status=status
        )
        
        # Calculate total pages
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return RuleResultListResponse(
            results=[RuleResultResponse.model_validate(result) for result in paginated_results],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
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
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from typing import Optional, List, Tuple
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult


class RuleResultDAO:
    def __init__(self, db: Session):
        self.db = db

    def get_by_compliance_id(
            self, 
            compliance_id: int,
            skip: int = 0, 
            limit: int = 10, 
            keyword: Optional[str] = None, 
            status: Optional[str] = None) -> List[RuleResult]:
        
        query = self.db.query(RuleResult).filter(RuleResult.compliance_result_id == compliance_id)
        
        if keyword:
            query = query.filter(RuleResult.rule_name.ilike(f"%{keyword}%"))
        if status:
            query = query.filter(RuleResult.status == status)

        return query.offset(skip).limit(limit).all()

    def get_by_id(self, rule_result_id: int) -> Optional[RuleResult]:
        return self.db.query(RuleResult).filter(RuleResult.id == rule_result_id).first()

    def count_passed_rules(self, compliance_id: int) -> int:
        return self.db.query(func.count(RuleResult.id)).filter(
            and_(
                RuleResult.compliance_result_id == compliance_id,
                RuleResult.status == 'passed'
            )
        ).scalar()
    
    def count_by_compliance_id(self, compliance_id: int) -> int:
        return self.db.query(func.count(RuleResult.id)).filter(
            RuleResult.compliance_result_id == compliance_id
        ).scalar()
    
    def count_filtered(self, compliance_id: int, keyword: Optional[str] = None, status: Optional[str] = None) -> int:
        query = self.db.query(func.count(RuleResult.id)).filter(RuleResult.compliance_result_id == compliance_id)
        
        if keyword:
            query = query.filter(RuleResult.rule_name.ilike(f"%{keyword}%"))
        if status:
            query = query.filter(RuleResult.status == status)
            
        return query.scalar()
    
    def create(self, rule_result: RuleResult) -> RuleResult:
        try:
            self.db.add(rule_result)
            self.db.commit()
            self.db.refresh(rule_result)
            return rule_result
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e

    def create_bulk(self, rule_results: List[RuleResult]) -> List[RuleResult]:
        try:
            self.db.add_all(rule_results)
            self.db.commit()
            for rule_result in rule_results:
                self.db.refresh(rule_result)
            return rule_results
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e

    def update(self, rule_result: RuleResult) -> RuleResult:
        try:
            self.db.commit()
            self.db.refresh(rule_result)
            return rule_result
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e

  
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from typing import Optional, List, Tuple
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
from schemas.compliance import ComplianceResultCreate, ComplianceResultUpdate

class RuleResultDAO:
    def __init__(self, db: Session):
        self.db = db

    def get_by_compliance_id(self, compliance_id: int) -> List[RuleResult]:
        return self.db.query(RuleResult).filter(
            RuleResult.compliance_result_id == compliance_id
        ).all()

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

    def delete(self, rule_result_id: int) -> bool:
        try:
            rule_result = self.db.query(RuleResult).filter(RuleResult.id == rule_result_id).first()
            if rule_result:
                self.db.delete(rule_result)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            raise e
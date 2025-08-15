from typing import Optional, List
from sqlalchemy.orm import Session
from models.rule_result import RuleResult


class RuleResultDAO:
    
    @staticmethod
    def get_all_rule_results(db: Session) -> List[RuleResult]:
        """Get all rule results"""
        return db.query(RuleResult).all()
    
    @staticmethod
    def get_rule_result_by_id(db: Session, result_id: int) -> Optional[RuleResult]:
        """Get rule result by ID"""
        return db.query(RuleResult).filter(RuleResult.id == result_id).first()
    
    @staticmethod
    def get_rule_results_by_compliance_result(db: Session, compliance_result_id: int) -> List[RuleResult]:
        """Get rule results by compliance result ID"""
        return db.query(RuleResult).filter(
            RuleResult.compliance_result_id == compliance_result_id
        ).all()
    
    @staticmethod
    def get_rule_results_by_rule(db: Session, rule_id: int) -> List[RuleResult]:
        """Get rule results by rule ID"""
        return db.query(RuleResult).filter(
            RuleResult.rule_id == rule_id
        ).order_by(RuleResult.created_at.desc()).all()
    
    @staticmethod
    def create_rule_result(
        db: Session, 
        compliance_result_id: int, 
        rule_id: int, 
        status: str, 
        message: str = None,
        details: str = None
    ) -> RuleResult:
        """Create a new rule result"""
        db_result = RuleResult(
            compliance_result_id=compliance_result_id,
            rule_id=rule_id,
            status=status,
            message=message,
            details=details
        )
        db.add(db_result)
        db.commit()
        db.refresh(db_result)
        return db_result
    
    @staticmethod
    def get_failed_rule_results(db: Session, compliance_result_id: int) -> List[RuleResult]:
        """Get failed rule results by compliance result ID"""
        return db.query(RuleResult).filter(
            RuleResult.compliance_result_id == compliance_result_id,
            RuleResult.status == "failed"
        ).all()
    
    @staticmethod
    def get_passed_rule_results(db: Session, compliance_result_id: int) -> List[RuleResult]:
        """Get passed rule results by compliance result ID"""
        return db.query(RuleResult).filter(
            RuleResult.compliance_result_id == compliance_result_id,
            RuleResult.status == "passed"
        ).all()
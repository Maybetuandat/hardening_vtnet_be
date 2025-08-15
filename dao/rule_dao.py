from typing import Optional, List
from sqlalchemy.orm import Session
from models.rule import Rule


class RuleDAO:
    
    @staticmethod
    def get_all_rules(db: Session) -> List[Rule]:
        """Get all rules"""
        return db.query(Rule).all()
    
    @staticmethod
    def get_rule_by_id(db: Session, rule_id: int) -> Optional[Rule]:
        """Get rule by ID"""
        return db.query(Rule).filter(Rule.id == rule_id).first()
    
    @staticmethod
    def get_rules_by_security_standard(db: Session, security_standard_id: int) -> List[Rule]:
        """Get rules by security standard ID"""
        return db.query(Rule).filter(
            Rule.security_standard_id == security_standard_id,
            Rule.is_active == True
        ).all()
    
    @staticmethod
    def get_active_rules(db: Session) -> List[Rule]:
        """Get all active rules"""
        return db.query(Rule).filter(Rule.is_active == True).all()

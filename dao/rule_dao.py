from typing import Optional, List
from sqlalchemy.orm import Session
from models.rule import Rule
from schemas.rule_schemas import RuleCreate, RuleUpdate


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
    
    @staticmethod
    def get_rule_by_name(db: Session, name: str) -> Optional[Rule]:
        """Get rule by name"""
        return db.query(Rule).filter(Rule.name == name).first()
    
    @staticmethod
    def exists_by_name(db: Session, name: str) -> bool:
        """Check if rule exists by name"""
        return db.query(Rule).filter(Rule.name == name).first() is not None
    
    @staticmethod
    def exists_by_name_exclude_id(db: Session, name: str, rule_id: int) -> bool:
        """Check if rule exists by name excluding specific ID"""
        return db.query(Rule).filter(
            Rule.name == name,
            Rule.id != rule_id
        ).first() is not None
    
    @staticmethod
    def create_rule(db: Session, rule_data: RuleCreate) -> Rule:
        """Create a new rule"""
        db_rule = Rule(
            name=rule_data.name,
            description=rule_data.description,
            severity=rule_data.severity,
            security_standard_id=rule_data.security_standard_id,
            parameters=rule_data.parameters,
            is_active=rule_data.is_active
        )
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)
        return db_rule
    
    @staticmethod
    def update_rule(db: Session, rule_id: int, rule_data: RuleUpdate) -> Optional[Rule]:
        """Update an existing rule"""
        db_rule = db.query(Rule).filter(Rule.id == rule_id).first()
        if not db_rule:
            return None

        # Update only provided fields
        update_data = rule_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_rule, field, value)

        db.commit()
        db.refresh(db_rule)
        return db_rule
    
    @staticmethod
    def delete_rule(db: Session, rule_id: int) -> bool:
        """Delete a rule"""
        db_rule = db.query(Rule).filter(Rule.id == rule_id).first()
        if not db_rule:
            return False

        db.delete(db_rule)
        db.commit()
        return True
    
    @staticmethod
    def get_rules_by_severity(db: Session, severity: str) -> List[Rule]:
        """Get rules by severity"""
        return db.query(Rule).filter(
            Rule.severity == severity,
            Rule.is_active == True
        ).all()
    
    @staticmethod
    def get_rules_count_by_security_standard(db: Session, security_standard_id: int) -> int:
        """Get count of rules in a security standard"""
        return db.query(Rule).filter(
            Rule.security_standard_id == security_standard_id,
            Rule.is_active == True
        ).count()
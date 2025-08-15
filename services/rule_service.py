from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from dao.rule_dao import RuleDAO
from dao.security_standard_dao import SecurityStandardDao
from models.rule import Rule
from schemas.rule_schemas import RuleCreate, RuleUpdate, RuleResponse, RuleWithSecurityStandardResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class RuleService:
    """Service layer for Rule operations"""

    @staticmethod
    def get_all_rules(db: Session) -> List[RuleWithSecurityStandardResponse]:
        """Get all rules with security standard information"""
        try:
            logger.info("Fetching all rules from database")
            rules = RuleDAO.get_all_rules(db)
            logger.info(f"Found {len(rules)} rules")
            return [RuleService._to_response_with_security_standard(db, rule) for rule in rules]
        except Exception as e:
            logger.error(f"Error fetching rules: {str(e)}")
            raise

    @staticmethod
    def get_rule_by_id(db: Session, rule_id: int) -> Optional[RuleWithSecurityStandardResponse]:
        """Get rule by ID with security standard information"""
        try:
            logger.info(f"Fetching rule with ID: {rule_id}")
            rule = RuleDAO.get_rule_by_id(db, rule_id)
            if rule:
                logger.info(f"Found rule: {rule.name}")
                return RuleService._to_response_with_security_standard(db, rule)
            else:
                logger.warning(f"Rule with ID {rule_id} not found")
                return None
        except Exception as e:
            logger.error(f"Error fetching rule: {str(e)}")
            raise

    @staticmethod
    def create_rule(db: Session, rule_data: RuleCreate) -> RuleResponse:
        """Create a new rule"""
        try:
            logger.info(f"Creating new rule: {rule_data.name}")
            
            # Validate security standard exists
            security_standard = SecurityStandardDao.get_security_standard_by_id(db, rule_data.security_standard_id)
            if not security_standard:
                raise ValueError(f"Security standard with ID {rule_data.security_standard_id} does not exist")
            
            # Check if rule with same name already exists
            if RuleDAO.exists_by_name(db, rule_data.name):
                raise ValueError(f"Rule with name '{rule_data.name}' already exists")
            
            rule = RuleDAO.create_rule(db, rule_data)
            logger.info(f"Rule created successfully: {rule.name}")
            return RuleService._to_response(rule)
        except ValueError as e:
            logger.error(f"Validation error creating rule: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating rule: {str(e)}")
            raise

    @staticmethod
    def update_rule(db: Session, rule_id: int, rule_data: RuleUpdate) -> Optional[RuleResponse]:
        """Update an existing rule"""
        try:
            logger.info(f"Updating rule with ID: {rule_id}")
            
            # Check if rule exists
            existing_rule = RuleDAO.get_rule_by_id(db, rule_id)
            if not existing_rule:
                logger.warning(f"Rule with ID {rule_id} not found for update")
                return None
            
            # Validate security standard exists (if being updated)
            if rule_data.security_standard_id:
                security_standard = SecurityStandardDao.get_security_standard_by_id(db, rule_data.security_standard_id)
                if not security_standard:
                    raise ValueError(f"Security standard with ID {rule_data.security_standard_id} does not exist")
            
            # Check if new name conflicts with existing rule (if name is being updated)
            if rule_data.name and rule_data.name != existing_rule.name:
                if RuleDAO.exists_by_name_exclude_id(db, rule_data.name, rule_id):
                    raise ValueError(f"Rule with name '{rule_data.name}' already exists")
            
            updated_rule = RuleDAO.update_rule(db, rule_id, rule_data)
            if updated_rule:
                logger.info(f"Rule updated successfully: {updated_rule.name}")
                return RuleService._to_response(updated_rule)
            return None
        except ValueError as e:
            logger.error(f"Validation error updating rule: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating rule: {str(e)}")
            raise

    @staticmethod
    def delete_rule(db: Session, rule_id: int) -> bool:
        """Delete a rule"""
        try:
            logger.info(f"Deleting rule with ID: {rule_id}")
            
            # Check if rule exists
            existing_rule = RuleDAO.get_rule_by_id(db, rule_id)
            if not existing_rule:
                logger.warning(f"Rule with ID {rule_id} not found for deletion")
                return False
            
            # TODO: Check if rule is being used by any rule results
            # This should be implemented based on business requirements
            
            success = RuleDAO.delete_rule(db, rule_id)
            if success:
                logger.info(f"Rule with ID {rule_id} deleted successfully")
            return success
        except Exception as e:
            logger.error(f"Error deleting rule: {str(e)}")
            raise

    @staticmethod
    def get_rules_by_security_standard(db: Session, security_standard_id: int) -> List[RuleResponse]:
        """Get rules by security standard ID"""
        try:
            logger.info(f"Fetching rules for security standard: {security_standard_id}")
            rules = RuleDAO.get_rules_by_security_standard(db, security_standard_id)
            logger.info(f"Found {len(rules)} rules for security standard {security_standard_id}")
            return [RuleService._to_response(rule) for rule in rules]
        except Exception as e:
            logger.error(f"Error fetching rules by security standard: {str(e)}")
            raise

    @staticmethod
    def get_active_rules(db: Session) -> List[RuleWithSecurityStandardResponse]:
        """Get only active rules"""
        try:
            logger.info("Fetching active rules")
            rules = RuleDAO.get_active_rules(db)
            logger.info(f"Found {len(rules)} active rules")
            return [RuleService._to_response_with_security_standard(db, rule) for rule in rules]
        except Exception as e:
            logger.error(f"Error fetching active rules: {str(e)}")
            raise

    @staticmethod
    def get_rules_by_severity(db: Session, severity: str) -> List[RuleWithSecurityStandardResponse]:
        """Get rules by severity"""
        try:
            logger.info(f"Fetching rules with severity: {severity}")
            rules = RuleDAO.get_rules_by_severity(db, severity)
            logger.info(f"Found {len(rules)} rules with severity {severity}")
            return [RuleService._to_response_with_security_standard(db, rule) for rule in rules]
        except Exception as e:
            logger.error(f"Error fetching rules by severity: {str(e)}")
            raise

    @staticmethod
    def _to_response(rule: Rule) -> RuleResponse:
        """Convert Rule model to RuleResponse"""
        return RuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            severity=rule.severity,
            security_standard_id=rule.security_standard_id,
            parameters=rule.parameters,
            is_active=rule.is_active,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )

    @staticmethod
    def _to_response_with_security_standard(db: Session, rule: Rule) -> RuleWithSecurityStandardResponse:
        """Convert Rule model to RuleWithSecurityStandardResponse"""
        security_standard = SecurityStandardDao.get_security_standard_by_id(db, rule.security_standard_id)
        
        return RuleWithSecurityStandardResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            severity=rule.severity,
            security_standard_id=rule.security_standard_id,
            security_standard_name=security_standard.name if security_standard else None,
            security_standard_version=security_standard.version if security_standard else None,
            parameters=rule.parameters,
            is_active=rule.is_active,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
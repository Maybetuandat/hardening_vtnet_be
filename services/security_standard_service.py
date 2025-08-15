from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from dao.security_standard_dao import SecurityStandardDao
from models.security_standard import SecurityStandard
from schemas.security_standard_schemas import SecurityStandardCreate, SecurityStandardUpdate, SecurityStandardResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class SecurityStandardService:
    """Service layer for Security Standard operations"""

    @staticmethod
    def get_all_security_standards(db: Session) -> List[SecurityStandardResponse]:
        """Get all security standards"""
        try:
            logger.info("Fetching all security standards from database")
            security_standards = SecurityStandardDao.get_all_security_standards(db)
            logger.info(f"Found {len(security_standards)} security standards")
            return [SecurityStandardService._to_response(ss) for ss in security_standards]
        except Exception as e:
            logger.error(f"Error fetching security standards: {str(e)}")
            raise

    @staticmethod
    def get_security_standard_by_id(db: Session, security_standard_id: int) -> Optional[SecurityStandardResponse]:
        """Get security standard by ID"""
        try:
            logger.info(f"Fetching security standard with ID: {security_standard_id}")
            security_standard = SecurityStandardDao.get_security_standard_by_id(db, security_standard_id)
            if security_standard:
                logger.info(f"Found security standard: {security_standard.name}")
                return SecurityStandardService._to_response(security_standard)
            else:
                logger.warning(f"Security standard with ID {security_standard_id} not found")
                return None
        except Exception as e:
            logger.error(f"Error fetching security standard: {str(e)}")
            raise

    @staticmethod
    def create_security_standard(db: Session, security_standard_data: SecurityStandardCreate) -> SecurityStandardResponse:
        """Create a new security standard"""
        try:
            logger.info(f"Creating new security standard: {security_standard_data.name}")
            
            # Check if security standard with same name already exists
            if SecurityStandardDao.exists_by_name(db, security_standard_data.name):
                raise ValueError(f"Security standard with name '{security_standard_data.name}' already exists")
            
            security_standard = SecurityStandardDao.create_security_standard(db, security_standard_data)
            logger.info(f"Security standard created successfully: {security_standard.name}")
            return SecurityStandardService._to_response(security_standard)
        except ValueError as e:
            logger.error(f"Validation error creating security standard: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating security standard: {str(e)}")
            raise

    @staticmethod
    def update_security_standard(db: Session, security_standard_id: int, security_standard_data: SecurityStandardUpdate) -> Optional[SecurityStandardResponse]:
        """Update an existing security standard"""
        try:
            logger.info(f"Updating security standard with ID: {security_standard_id}")
            
            # Check if security standard exists
            existing_security_standard = SecurityStandardDao.get_security_standard_by_id(db, security_standard_id)
            if not existing_security_standard:
                logger.warning(f"Security standard with ID {security_standard_id} not found for update")
                return None
            
            # Check if new name conflicts with existing security standard (if name is being updated)
            if security_standard_data.name and security_standard_data.name != existing_security_standard.name:
                if SecurityStandardDao.exists_by_name_exclude_id(db, security_standard_data.name, security_standard_id):
                    raise ValueError(f"Security standard with name '{security_standard_data.name}' already exists")
            
            updated_security_standard = SecurityStandardDao.update_security_standard(db, security_standard_id, security_standard_data)
            if updated_security_standard:
                logger.info(f"Security standard updated successfully: {updated_security_standard.name}")
                return SecurityStandardService._to_response(updated_security_standard)
            return None
        except ValueError as e:
            logger.error(f"Validation error updating security standard: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating security standard: {str(e)}")
            raise

    @staticmethod
    def delete_security_standard(db: Session, security_standard_id: int) -> bool:
        """Delete a security standard"""
        try:
            logger.info(f"Deleting security standard with ID: {security_standard_id}")
            
            # Check if security standard exists
            existing_security_standard = SecurityStandardDao.get_security_standard_by_id(db, security_standard_id)
            if not existing_security_standard:
                logger.warning(f"Security standard with ID {security_standard_id} not found for deletion")
                return False
            
            # TODO: Check if security standard is being used by any rules or compliance results
            # This should be implemented based on business requirements
            
            success = SecurityStandardDao.delete_security_standard(db, security_standard_id)
            if success:
                logger.info(f"Security standard with ID {security_standard_id} deleted successfully")
            return success
        except Exception as e:
            logger.error(f"Error deleting security standard: {str(e)}")
            raise

    @staticmethod
    def get_active_security_standards(db: Session) -> List[SecurityStandardResponse]:
        """Get only active security standards"""
        try:
            logger.info("Fetching active security standards")
            security_standards = SecurityStandardDao.get_active_security_standards(db)
            logger.info(f"Found {len(security_standards)} active security standards")
            return [SecurityStandardService._to_response(ss) for ss in security_standards]
        except Exception as e:
            logger.error(f"Error fetching active security standards: {str(e)}")
            raise

    @staticmethod
    def get_security_standards_by_version(db: Session, version: str) -> List[SecurityStandardResponse]:
        """Get security standards by version"""
        try:
            logger.info(f"Fetching security standards with version: {version}")
            security_standards = SecurityStandardDao.get_security_standards_by_version(db, version)
            logger.info(f"Found {len(security_standards)} security standards with version {version}")
            return [SecurityStandardService._to_response(ss) for ss in security_standards]
        except Exception as e:
            logger.error(f"Error fetching security standards by version: {str(e)}")
            raise

    @staticmethod
    def _to_response(security_standard: SecurityStandard) -> SecurityStandardResponse:
        """Convert SecurityStandard model to SecurityStandardResponse"""
        return SecurityStandardResponse(
            id=security_standard.id,
            name=security_standard.name,
            description=security_standard.description,
            version=security_standard.version,
            is_active=security_standard.is_active,
            created_at=security_standard.created_at,
            updated_at=security_standard.updated_at
        )
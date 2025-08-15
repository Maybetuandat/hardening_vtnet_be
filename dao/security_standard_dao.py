from typing import List, Optional
from sqlalchemy.orm import Session
from models.security_standard import SecurityStandard
from schemas.security_standard_schemas import SecurityStandardCreate, SecurityStandardUpdate


class SecurityStandardDao:
    """Data Access Object for Security Standard operations"""

    @staticmethod
    def get_all_security_standards(db: Session) -> List[SecurityStandard]:
        """Get all security standards"""
        return db.query(SecurityStandard).all()

    @staticmethod
    def get_security_standard_by_id(db: Session, security_standard_id: int) -> Optional[SecurityStandard]:
        """Get security standard by ID"""
        return db.query(SecurityStandard).filter(SecurityStandard.id == security_standard_id).first()

    @staticmethod
    def get_security_standard_by_name(db: Session, name: str) -> Optional[SecurityStandard]:
        """Get security standard by name"""
        return db.query(SecurityStandard).filter(SecurityStandard.name == name).first()

    @staticmethod
    def exists_by_name(db: Session, name: str) -> bool:
        """Check if security standard exists by name"""
        return db.query(SecurityStandard).filter(SecurityStandard.name == name).first() is not None

    @staticmethod
    def exists_by_name_exclude_id(db: Session, name: str, security_standard_id: int) -> bool:
        """Check if security standard exists by name excluding specific ID"""
        return db.query(SecurityStandard).filter(
            SecurityStandard.name == name,
            SecurityStandard.id != security_standard_id
        ).first() is not None

    @staticmethod
    def create_security_standard(db: Session, security_standard_data: SecurityStandardCreate) -> SecurityStandard:
        """Create a new security standard"""
        db_security_standard = SecurityStandard(
            name=security_standard_data.name,
            description=security_standard_data.description,
            version=security_standard_data.version,
            is_active=security_standard_data.is_active
        )
        db.add(db_security_standard)
        db.commit()
        db.refresh(db_security_standard)
        return db_security_standard

    @staticmethod
    def update_security_standard(db: Session, security_standard_id: int, security_standard_data: SecurityStandardUpdate) -> Optional[SecurityStandard]:
        """Update an existing security standard"""
        db_security_standard = db.query(SecurityStandard).filter(SecurityStandard.id == security_standard_id).first()
        if not db_security_standard:
            return None

        # Update only provided fields
        update_data = security_standard_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_security_standard, field, value)

        db.commit()
        db.refresh(db_security_standard)
        return db_security_standard

    @staticmethod
    def delete_security_standard(db: Session, security_standard_id: int) -> bool:
        """Delete a security standard"""
        db_security_standard = db.query(SecurityStandard).filter(SecurityStandard.id == security_standard_id).first()
        if not db_security_standard:
            return False

        db.delete(db_security_standard)
        db.commit()
        return True

    @staticmethod
    def get_active_security_standards(db: Session) -> List[SecurityStandard]:
        """Get only active security standards"""
        return db.query(SecurityStandard).filter(SecurityStandard.is_active == True).all()

    @staticmethod
    def get_security_standards_by_version(db: Session, version: str) -> List[SecurityStandard]:
        """Get security standards by version"""
        return db.query(SecurityStandard).filter(SecurityStandard.version == version).all()
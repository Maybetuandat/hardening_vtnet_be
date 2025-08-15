from typing import Optional, List
from sqlalchemy.orm import Session
from models.compliance_result import ComplianceResult
from datetime import datetime


class ComplianceResultDAO:
    
    @staticmethod
    def get_all_compliance_results(db: Session) -> List[ComplianceResult]:
        """Get all compliance results"""
        return db.query(ComplianceResult).all()
    
    @staticmethod
    def get_compliance_result_by_id(db: Session, result_id: int) -> Optional[ComplianceResult]:
        """Get compliance result by ID"""
        return db.query(ComplianceResult).filter(ComplianceResult.id == result_id).first()
    
    @staticmethod
    def get_compliance_results_by_server(db: Session, server_id: int) -> List[ComplianceResult]:
        """Get compliance results by server ID"""
        return db.query(ComplianceResult).filter(
            ComplianceResult.server_id == server_id
        ).order_by(ComplianceResult.scan_date.desc()).all()
    
    @staticmethod
    def get_compliance_results_by_security_standard(db: Session, security_standard_id: int) -> List[ComplianceResult]:
        """Get compliance results by security standard ID"""
        return db.query(ComplianceResult).filter(
            ComplianceResult.security_standard_id == security_standard_id
        ).order_by(ComplianceResult.scan_date.desc()).all()
    
    @staticmethod
    def get_latest_compliance_result(db: Session, server_id: int, security_standard_id: int) -> Optional[ComplianceResult]:
        """Get latest compliance result for server and security standard"""
        return db.query(ComplianceResult).filter(
            ComplianceResult.server_id == server_id,
            ComplianceResult.security_standard_id == security_standard_id
        ).order_by(ComplianceResult.scan_date.desc()).first()
    
    @staticmethod
    def create_compliance_result(db: Session, server_id: int, security_standard_id: int, total_rules: int) -> ComplianceResult:
        """Create a new compliance result"""
        db_result = ComplianceResult(
            server_id=server_id,
            security_standard_id=security_standard_id,
            status="running",
            total_rules=total_rules,
            scan_date=datetime.now()
        )
        db.add(db_result)
        db.commit()
        db.refresh(db_result)
        return db_result
    
    @staticmethod
    def update_compliance_result(
        db: Session, 
        result_id: int, 
        status: str, 
        passed_rules: int = 0, 
        failed_rules: int = 0, 
        score: int = 0
    ) -> Optional[ComplianceResult]:
        """Update compliance result"""
        db_result = db.query(ComplianceResult).filter(ComplianceResult.id == result_id).first()
        if not db_result:
            return None
        
        db_result.status = status
        db_result.passed_rules = passed_rules
        db_result.failed_rules = failed_rules
        db_result.score = score
        
        db.commit()
        db.refresh(db_result)
        return db_result
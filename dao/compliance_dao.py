from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from typing import Optional, List, Tuple
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
from schemas.compliance import ComplianceResultCreate, ComplianceResultUpdate


class ComplianceDAO:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 10) -> Tuple[List[ComplianceResult], int]:
        query = self.db.query(ComplianceResult)
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return results, total

    def get_by_id(self, compliance_id: int) -> Optional[ComplianceResult]:
        return self.db.query(ComplianceResult).filter(ComplianceResult.id == compliance_id).first()

    def create(self, compliance: ComplianceResult) -> ComplianceResult:
        try:
            self.db.add(compliance)
            self.db.commit()
            self.db.refresh(compliance)
            return compliance
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e

    def update(self, compliance: ComplianceResult) -> ComplianceResult:
        try:
            self.db.commit()
            self.db.refresh(compliance)
            return compliance
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, compliance_id: int) -> bool:
        try:
            compliance = self.get_by_id(compliance_id)
            if compliance:
                self.db.delete(compliance)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            raise e

    def search_compliance_results(
        self,
        server_id: Optional[int] = None,
        workload_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[ComplianceResult], int]:
        query = self.db.query(ComplianceResult)
        
        # Filter by server_id
        if server_id is not None:
            query = query.filter(ComplianceResult.server_id == server_id)
        
        # Filter by workload_id - join với Server table
        if workload_id is not None:
            from models.server import Server
            query = query.join(Server).filter(Server.workload_id == workload_id)
        
        # Filter by status
        if status and status.strip():
            query = query.filter(ComplianceResult.status == status.strip())
        
        total = query.count()
        results = query.order_by(ComplianceResult.scan_date.desc()).offset(skip).limit(limit).all()
        
        return results, total

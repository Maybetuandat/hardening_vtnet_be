from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from typing import Optional, List, Tuple
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
from models.server import Server
from schemas.compliance import ComplianceResultCreate, ComplianceResultUpdate
from datetime import datetime, timedelta

class ComplianceDAO:
    def __init__(self, db: Session):
        self.db = db


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
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        today: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[ComplianceResult], int]:
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

        query = self.db.query(ComplianceResult)

        
        if server_id:
            query = query.filter(ComplianceResult.server_id == server_id)

        
        if keyword and keyword.strip():
            keyword = keyword.strip()
            conditions = []

            
            conditions.append(
                func.lower(Server.ip_address).like(f"%{keyword.lower()}%")
            )

           

            query = query.join(ComplianceResult.server).filter(or_(*conditions))

        
        if status and status.strip():
            query = query.filter(ComplianceResult.status == status.strip())

        if today:
            query = query.filter(
                ComplianceResult.scan_date >= today_start,
                ComplianceResult.scan_date <= today_end
            )
        
        total = query.count()
        results = (
            query.order_by(ComplianceResult.scan_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return results, total
    

    def get_today_compliance_results(
        self,
        server_id: Optional[int] = None,
        keyword: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ComplianceResult]:
       
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

        
        query = self.db.query(ComplianceResult).options(
            joinedload(ComplianceResult.server).joinedload(Server.workload)
        ).join(Server)

        
        query = query.filter(
            and_(
                ComplianceResult.scan_date >= today_start,
                ComplianceResult.scan_date <= today_end
            )
        )

        
        if server_id:
            query = query.filter(ComplianceResult.server_id == server_id)

        if keyword and keyword.strip():
            query = query.filter(
                func.lower(Server.ip_address).like(func.lower(f"%{keyword.strip()}%"))
            )

        if status:
            query = query.filter(ComplianceResult.status == status)

        
        return query.order_by(ComplianceResult.scan_date.desc()).all()
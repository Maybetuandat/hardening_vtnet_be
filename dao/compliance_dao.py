from sqlalchemy.orm import Session
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
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[ComplianceResult], int]:
        query = self.db.query(ComplianceResult)

        # filter by server_id
        if server_id:
            query = query.filter(ComplianceResult.server_id == server_id)

        # filter by keyword (ip or scan_date)
        if keyword and keyword.strip():
            keyword = keyword.strip()
            conditions = []

            # search theo ip
            conditions.append(
                func.lower(Server.ip_address).like(f"%{keyword.lower()}%")
            )

            # thử parse keyword như date hoặc datetime
            for fmt in ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    date_val = datetime.strptime(keyword, fmt)

                    if "%H:%M" in fmt:
                        # Nếu có giờ: lọc trong 1 giờ
                        start = date_val
                        end = date_val + timedelta(hours=1)
                    else:
                        # Nếu chỉ có ngày: lọc trong nguyên ngày
                        start = date_val
                        end = date_val + timedelta(days=1)

                    conditions.append(
                        ComplianceResult.scan_date.between(start, end)
                    )
                    break
                except ValueError:
                    continue

            query = query.join(ComplianceResult.server).filter(or_(*conditions))

        # filter by status
        if status and status.strip():
            query = query.filter(ComplianceResult.status == status.strip())

        # count + paging
        total = query.count()
        results = (
            query.order_by(ComplianceResult.scan_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return results, total
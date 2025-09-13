from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc, distinct
from sqlalchemy.sql import text
from typing import Optional, List, Tuple
from models.compliance_result import ComplianceResult
from models.server import Server
from models.workload import WorkLoad
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
            compliance.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(compliance)
            return compliance
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, compliance: ComplianceResult) -> bool:
        try:
            self.db.delete(compliance)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def search_compliance_results(
        self,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        today: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[ComplianceResult], int]:
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

        if today:
            # Khi có today, lấy compliance duy nhất cho mỗi IP (compliance gần nhất)
            # Sử dụng window function để rank theo thời gian scan
            subquery = (
                self.db.query(
                    ComplianceResult.id,
                    func.row_number()
                    .over(
                        partition_by=Server.ip_address,
                        order_by=desc(ComplianceResult.scan_date)
                    )
                    .label('rn')
                )
                .join(ComplianceResult.server)
                .filter(
                    and_(
                        ComplianceResult.scan_date >= today_start,
                        ComplianceResult.scan_date <= today_end
                    )
                )
            )

            # Áp dụng filter nếu có keyword
            

        if keyword and keyword.strip():
                keyword = keyword.strip()
                subquery = subquery.filter(
                    func.lower(Server.ip_address).like(f"%{keyword.lower()}%")
                )

            # Áp dụng filter theo status
        if status and status.strip():
                subquery = subquery.filter(ComplianceResult.status == status.strip())

        subquery = subquery.subquery()

            # Query chính để lấy compliance result với rank = 1 (gần nhất cho mỗi IP)
        query = (
                self.db.query(ComplianceResult)
                .join(subquery, ComplianceResult.id == subquery.c.id)
                .filter(subquery.c.rn == 1)
            )

            # Đếm tổng số record
        total = query.count()

            # Lấy kết quả với pagination
        results = (
                query.order_by(ComplianceResult.scan_date.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )

        return results, total

    def get_today_compliance_results(
        self,
        list_workload_id: Optional[List[int]] = None,
        keyword: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ComplianceResult]:
       
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

        # Query với eager loading
        query = self.db.query(ComplianceResult).options(
            joinedload(ComplianceResult.server).joinedload(Server.workload)
        ).join(Server)

        # Filter theo thời gian hôm nay
        query = query.filter(
            and_(
                ComplianceResult.scan_date >= today_start,
                ComplianceResult.scan_date <= today_end
            )
        )

        # Filter theo workload IDs
        if list_workload_id and len(list_workload_id) > 0:
            query = query.join(Server.workload).filter(WorkLoad.id.in_(list_workload_id))

        # Filter theo keyword (IP address)
        if keyword and keyword.strip():
            keyword = keyword.strip().lower()
            query = query.join(Server.workload).filter(func.lower(Server.ip_address).like(f"%{keyword}%"))

        # Filter theo status
        if status:
            query = query.filter(ComplianceResult.status == status)

        return query.order_by(ComplianceResult.scan_date.desc()).all()
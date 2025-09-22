# dao/fix_action_log_dao.py
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta
from models.fix_action_log import FixActionLog

class FixActionLogDAO:
    def __init__(self, db: Session):
        self.db = db

    def create(self, fix_log: FixActionLog) -> FixActionLog:
        try:
            self.db.add(fix_log)
            self.db.commit()
            self.db.refresh(fix_log)
            return fix_log
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, log_id: int) -> Optional[FixActionLog]:
        return self.db.query(FixActionLog).filter(FixActionLog.id == log_id).first()

    def get_by_compliance_id(
        self,
        compliance_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[FixActionLog], int]:
        try:
            query = self.db.query(FixActionLog).filter(
                FixActionLog.compliance_result_id == compliance_id
            )
            total = query.count()
            logs = (
                query.order_by(desc(FixActionLog.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
            return logs, total
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_rule_result_id(
        self,
        rule_result_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[FixActionLog], int]:
        try:
            query = self.db.query(FixActionLog).filter(
                FixActionLog.rule_result_id == rule_result_id
            )
            total = query.count()
            logs = (
                query.order_by(desc(FixActionLog.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
            return logs, total
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[FixActionLog], int]:
        try:
            query = self.db.query(FixActionLog).filter(
                FixActionLog.user_id == user_id
            )
            total = query.count()
            logs = (
                query.order_by(desc(FixActionLog.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
            return logs, total
        except Exception as e:
            self.db.rollback()
            raise e

    def search_fix_logs(
        self,
        keyword: Optional[str] = None,
        user_id: Optional[int] = None,
        compliance_id: Optional[int] = None,
        rule_result_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        is_success: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[FixActionLog], int]:
        try:
            query = self.db.query(FixActionLog)
            
            conditions = []
            
            if keyword and keyword.strip():
                conditions.append(
                    or_(
                        FixActionLog.username.ilike(f"%{keyword.strip()}%"),
                        FixActionLog.rule_name.ilike(f"%{keyword.strip()}%"),
                        FixActionLog.command.ilike(f"%{keyword.strip()}%"),
                        FixActionLog.execution_output.ilike(f"%{keyword.strip()}%")
                    )
                )
            
            if user_id:
                conditions.append(FixActionLog.user_id == user_id)
            
            if compliance_id:
                conditions.append(FixActionLog.compliance_result_id == compliance_id)
            
            if rule_result_id:
                conditions.append(FixActionLog.rule_result_id == rule_result_id)
            
            if old_status:
                conditions.append(FixActionLog.old_status == old_status)
            
            if new_status:
                conditions.append(FixActionLog.new_status == new_status)
            
            if is_success is not None:
                conditions.append(FixActionLog.is_success == is_success)
            
            if start_date:
                conditions.append(FixActionLog.created_at >= start_date)
            
            if end_date:
                conditions.append(FixActionLog.created_at <= end_date)
            
            if conditions:
                query = query.filter(and_(*conditions))
            
            total = query.count()
            logs = (
                query.order_by(desc(FixActionLog.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            return logs, total
        except Exception as e:
            self.db.rollback()
            raise e

    def get_recent_fix_logs(
        self,
        hours: int = 24,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[FixActionLog], int]:
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = self.db.query(FixActionLog).filter(
                FixActionLog.created_at >= since
            )
            
            total = query.count()
            logs = (
                query.order_by(desc(FixActionLog.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            return logs, total
        except Exception as e:
            self.db.rollback()
            raise e

    def get_failed_fix_logs(
        self,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[FixActionLog], int]:
        try:
            query = self.db.query(FixActionLog).filter(
                FixActionLog.is_success == False
            )
            
            total = query.count()
            logs = (
                query.order_by(desc(FixActionLog.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            return logs, total
        except Exception as e:
            self.db.rollback()
            raise e
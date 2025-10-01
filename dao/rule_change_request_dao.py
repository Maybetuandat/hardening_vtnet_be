from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from models.rule_change_request import RuleChangeRequest
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RuleChangeRequestDAO:  
    def __init__(self, db: Session):
        self.db = db
    def create(self, request: RuleChangeRequest) -> RuleChangeRequest:
        try:
            self.db.add(request)
            self.db.commit()
            self.db.refresh(request)
            return request
        except Exception as e:
            self.db.rollback()
            logger.error(f" Error creating RuleChangeRequest: {e}")
            raise
    
  
    def get_by_id(self, request_id: int, user_id: Optional[int] = None) -> Optional[RuleChangeRequest]:
        query = self.db.query(RuleChangeRequest)
        if user_id:
            query = query.filter(RuleChangeRequest.user_id == user_id)
        return query.filter(RuleChangeRequest.id == request_id).first()
    
    def get_all_pending(self, limit: int = 100) -> List[RuleChangeRequest]:
        """Lấy tất cả pending requests"""
        try:
            return self.db.query(RuleChangeRequest)\
                .options(
                    joinedload(RuleChangeRequest.workload),
                    joinedload(RuleChangeRequest.rule),
                    joinedload(RuleChangeRequest.requester)
                )\
                .filter(RuleChangeRequest.status == 'pending')\
                .order_by(RuleChangeRequest.created_at.desc())\
                .limit(limit)\
                .all()
        except Exception as e:
            logger.error(f"❌ Error getting pending requests: {e}")
            return []
    
    def get_by_user(self, user_id: int, limit: int = 50) -> List[RuleChangeRequest]:
        """Lấy tất cả requests của 1 user"""
        try:
            return self.db.query(RuleChangeRequest)\
                .options(
                    joinedload(RuleChangeRequest.workload),
                    joinedload(RuleChangeRequest.rule),
                    joinedload(RuleChangeRequest.admin)
                )\
                .filter(RuleChangeRequest.user_id == user_id)\
                .order_by(RuleChangeRequest.created_at.desc())\
                .limit(limit)\
                .all()
        except Exception as e:
            logger.error(f"❌ Error getting requests by user {user_id}: {e}")
            return []
    
    def get_by_workload(
        self, 
        workload_id: int, 
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[RuleChangeRequest]:
        """Lấy requests theo workload"""
        try:
            query = self.db.query(RuleChangeRequest)\
                .options(
                    joinedload(RuleChangeRequest.rule),
                    joinedload(RuleChangeRequest.requester),
                    joinedload(RuleChangeRequest.admin)
                )\
                .filter(RuleChangeRequest.workload_id == workload_id)
            
            if status:
                query = query.filter(RuleChangeRequest.status == status)
            
            return query.order_by(RuleChangeRequest.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"❌ Error getting requests by workload {workload_id}: {e}")
            return []
    
    def get_by_rule(self, rule_id: int, status: Optional[str] = None) -> List[RuleChangeRequest]:
        """Lấy requests theo rule"""
        try:
            query = self.db.query(RuleChangeRequest)\
                .options(
                    joinedload(RuleChangeRequest.workload),
                    joinedload(RuleChangeRequest.requester),
                    joinedload(RuleChangeRequest.admin)
                )\
                .filter(RuleChangeRequest.rule_id == rule_id)
            
            if status:
                query = query.filter(RuleChangeRequest.status == status)
            
            return query.order_by(RuleChangeRequest.created_at.desc()).all()
        except Exception as e:
            logger.error(f"❌ Error getting requests by rule {rule_id}: {e}")
            return []
    
    # ===== UPDATE =====
    def update(self, request: RuleChangeRequest) -> RuleChangeRequest:
        """Update RuleChangeRequest"""
        try:
            request.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(request)
            logger.info(f"✅ Updated RuleChangeRequest ID: {request.id}")
            return request
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error updating RuleChangeRequest {request.id}: {e}")
            raise
    
    # ===== DELETE =====
    def delete(self, request_id: int) -> bool:
        """Xóa RuleChangeRequest"""
        try:
            request = self.get_by_id(request_id)
            if request:
                self.db.delete(request)
                self.db.commit()
                logger.info(f"✅ Deleted RuleChangeRequest ID: {request_id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error deleting RuleChangeRequest {request_id}: {e}")
            return False
    
    # ===== UTILITY =====
    def has_pending_request_for_rule(self, rule_id: int) -> bool:
        """
        Kiểm tra xem rule này đã có pending request chưa
        Dùng để tránh user spam nhiều request cho cùng 1 rule
        """
        try:
            count = self.db.query(RuleChangeRequest).filter(
                and_(
                    RuleChangeRequest.rule_id == rule_id,
                    RuleChangeRequest.status == 'pending'
                )
            ).count()
            return count > 0
        except Exception as e:
            logger.error(f"❌ Error checking pending request for rule {rule_id}: {e}")
            return False
    
    def count_pending_requests(self) -> int:
        """Đếm tổng số pending requests (dùng cho admin dashboard)"""
        try:
            return self.db.query(RuleChangeRequest)\
                .filter(RuleChangeRequest.status == 'pending')\
                .count()
        except Exception as e:
            logger.error(f"❌ Error counting pending requests: {e}")
            return 0
    
    def count_pending_by_workload(self, workload_id: int) -> int:
        """Đếm pending requests của 1 workload"""
        try:
            return self.db.query(RuleChangeRequest)\
                .filter(
                    and_(
                        RuleChangeRequest.workload_id == workload_id,
                        RuleChangeRequest.status == 'pending'
                    )
                )\
                .count()
        except Exception as e:
            logger.error(f"❌ Error counting pending requests for workload {workload_id}: {e}")
            return 0
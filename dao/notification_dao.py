# dao/notification_dao.py

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from models.notification import Notification
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NotificationDAO:
    """DAO for Notification operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== CREATE =====
    def create(self, notification: Notification) -> Notification:
        """Tạo mới notification"""
        try:
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            logger.info(f"✅ Created Notification ID: {notification.id} for user {notification.recipient_id}")
            return notification
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error creating Notification: {e}")
            raise
    
    def create_batch(self, notifications: List[Notification]) -> List[Notification]:
        """Tạo nhiều notifications cùng lúc (dùng cho notify tất cả admin)"""
        try:
            self.db.add_all(notifications)
            self.db.commit()
            for notif in notifications:
                self.db.refresh(notif)
            logger.info(f"✅ Created {len(notifications)} notifications")
            return notifications
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error creating batch notifications: {e}")
            raise
    
    # ===== READ =====
    def get_by_id(self, notification_id: int) -> Optional[Notification]:
        """Lấy notification theo ID"""
        try:
            return self.db.query(Notification)\
                .options(joinedload(Notification.recipient))\
                .filter(Notification.id == notification_id)\
                .first()
        except Exception as e:
            logger.error(f"❌ Error getting Notification by ID {notification_id}: {e}")
            return None
    
    def get_by_recipient(
        self, 
        recipient_id: int, 
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Lấy notifications của 1 user"""
        try:
            query = self.db.query(Notification)\
                .filter(Notification.recipient_id == recipient_id)
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
            
            return query.order_by(desc(Notification.created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"❌ Error getting notifications for recipient {recipient_id}: {e}")
            return []
    
    def get_by_type(
        self, 
        recipient_id: int, 
        notification_type: str,
        limit: int = 50
    ) -> List[Notification]:
        """Lấy notifications theo type"""
        try:
            return self.db.query(Notification)\
                .filter(
                    and_(
                        Notification.recipient_id == recipient_id,
                        Notification.type == notification_type
                    )
                )\
                .order_by(desc(Notification.created_at))\
                .limit(limit)\
                .all()
        except Exception as e:
            logger.error(f"❌ Error getting notifications by type {notification_type}: {e}")
            return []
    
    def get_by_reference(self, reference_id: int) -> List[Notification]:
        """Lấy tất cả notifications liên quan đến 1 RuleChangeRequest"""
        try:
            return self.db.query(Notification)\
                .filter(Notification.reference_id == reference_id)\
                .order_by(desc(Notification.created_at))\
                .all()
        except Exception as e:
            logger.error(f"❌ Error getting notifications by reference {reference_id}: {e}")
            return []
    
    # ===== UPDATE =====
    def mark_as_read(self, notification_id: int) -> Optional[Notification]:
        """Đánh dấu 1 notification là đã đọc"""
        try:
            notification = self.get_by_id(notification_id)
            if notification and not notification.is_read:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(notification)
                logger.info(f"✅ Marked notification {notification_id} as read")
            return notification
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error marking notification {notification_id} as read: {e}")
            return None
    
    def mark_all_as_read(self, recipient_id: int) -> int:
        """Đánh dấu tất cả notifications của user là đã đọc"""
        try:
            updated_count = self.db.query(Notification).filter(
                and_(
                    Notification.recipient_id == recipient_id,
                    Notification.is_read == False
                )
            ).update({
                "is_read": True,
                "read_at": datetime.utcnow()
            }, synchronize_session=False)
            
            self.db.commit()
            logger.info(f"✅ Marked {updated_count} notifications as read for user {recipient_id}")
            return updated_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error marking all notifications as read for user {recipient_id}: {e}")
            return 0
    
    # ===== DELETE =====
    def delete(self, notification_id: int) -> bool:
        """Xóa 1 notification"""
        try:
            notification = self.get_by_id(notification_id)
            if notification:
                self.db.delete(notification)
                self.db.commit()
                logger.info(f"✅ Deleted notification {notification_id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error deleting notification {notification_id}: {e}")
            return False
    
    def delete_by_reference(self, reference_id: int) -> int:
        """Xóa tất cả notifications liên quan đến 1 RuleChangeRequest"""
        try:
            deleted_count = self.db.query(Notification)\
                .filter(Notification.reference_id == reference_id)\
                .delete(synchronize_session=False)
            
            self.db.commit()
            logger.info(f"✅ Deleted {deleted_count} notifications for reference {reference_id}")
            return deleted_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error deleting notifications for reference {reference_id}: {e}")
            return 0
    
    # ===== UTILITY =====
    def get_unread_count(self, recipient_id: int) -> int:
        """Đếm số lượng unread notifications"""
        try:
            return self.db.query(Notification).filter(
                and_(
                    Notification.recipient_id == recipient_id,
                    Notification.is_read == False
                )
            ).count()
        except Exception as e:
            logger.error(f"❌ Error getting unread count for user {recipient_id}: {e}")
            return 0
    
    def get_unread_count_by_type(self, recipient_id: int, notification_type: str) -> int:
        """Đếm số lượng unread notifications theo type"""
        try:
            return self.db.query(Notification).filter(
                and_(
                    Notification.recipient_id == recipient_id,
                    Notification.type == notification_type,
                    Notification.is_read == False
                )
            ).count()
        except Exception as e:
            logger.error(f"❌ Error getting unread count by type for user {recipient_id}: {e}")
            return 0
# services/notification_service.py

from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from dao.notification_dao import NotificationDAO
from models.notification import Notification
from schemas.notification import NotificationResponse, NotificationListResponse, UnreadCountResponse

logger = logging.getLogger(__name__)

class NotificationService:
    """Service xử lý logic cho Notification"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_dao = NotificationDAO(db)
    
    # ===== QUERY METHODS =====
    
    def get_notifications(
        self, 
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> NotificationListResponse:
        """
        Lấy notifications của user với đầy đủ thông tin
        
        Returns NotificationListResponse với:
        - notifications: List[NotificationResponse]
        - total: int
        - unread_count: int
        """
        try:
            # Get notifications
            notifications = self.notification_dao.get_by_recipient(user_id, unread_only, limit)
            notification_responses = [self._convert_to_response(n) for n in notifications]
            
            # Get unread count
            unread_count = self.notification_dao.get_unread_count(user_id)
            
            return NotificationListResponse(
                notifications=notification_responses,
                total=len(notification_responses),
                unread_count=unread_count
            )
        except Exception as e:
            logger.error(f"❌ Error getting notifications: {e}")
            # Return empty response on error
            return NotificationListResponse(
                notifications=[],
                total=0,
                unread_count=0
            )
    
    def get_notification_by_id(self, notification_id: int) -> Optional[NotificationResponse]:
        """Lấy chi tiết 1 notification"""
        try:
            notification = self.notification_dao.get_by_id(notification_id)
            if notification:
                return self._convert_to_response(notification)
            return None
        except Exception as e:
            logger.error(f"❌ Error getting notification by ID: {e}")
            return None
    
    def get_unread_count(self, user_id: int) -> int:
        """Đếm số unread notifications"""
        try:
            return self.notification_dao.get_unread_count(user_id)
        except Exception as e:
            logger.error(f"❌ Error getting unread count: {e}")
            return 0
    
    # ===== UPDATE METHODS =====
    
    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """
        Đánh dấu notification là đã đọc
        Validate user_id để đảm bảo chỉ recipient mới mark được
        """
        try:
            notification = self.notification_dao.get_by_id(notification_id)
            
            if not notification:
                raise ValueError(f"Notification {notification_id} not found")
            
            # Validate ownership
            if notification.recipient_id != user_id:
                raise ValueError("You don't have permission to mark this notification as read")
            
            updated_notification = self.notification_dao.mark_as_read(notification_id)
            return updated_notification is not None
            
        except ValueError as e:
            logger.error(f"❌ Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error marking notification as read: {e}")
            raise
    
    def mark_all_as_read(self, user_id: int) -> int:
        """Đánh dấu tất cả notifications của user là đã đọc"""
        try:
            count = self.notification_dao.mark_all_as_read(user_id)
            logger.info(f"✅ Marked {count} notifications as read for user {user_id}")
            return count
        except Exception as e:
            logger.error(f"❌ Error marking all as read: {e}")
            raise
    
    # ===== DELETE METHODS =====
    
    def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """
        Xóa notification
        Validate user_id để đảm bảo chỉ recipient mới xóa được
        """
        try:
            notification = self.notification_dao.get_by_id(notification_id)
            
            if not notification:
                raise ValueError(f"Notification {notification_id} not found")
            
            # Validate ownership
            if notification.recipient_id != user_id:
                raise ValueError("You don't have permission to delete this notification")
            
            return self.notification_dao.delete(notification_id)
            
        except ValueError as e:
            logger.error(f"❌ Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error deleting notification: {e}")
            raise
    
    # ===== PRIVATE HELPER =====
    
    def _convert_to_response(self, notification: Notification) -> NotificationResponse:
        """Convert model to response DTO"""
        return NotificationResponse(
            id=notification.id,
            recipient_id=notification.recipient_id,
            type=notification.type,
            reference_id=notification.reference_id,
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            meta_data=notification.meta_data,
            created_at=notification.created_at,
            read_at=notification.read_at
        )
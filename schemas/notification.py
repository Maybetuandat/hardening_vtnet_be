# schemas/notification.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime

class NotificationResponse(BaseModel):
    id: int
    recipient_id: int
    type: Literal['rule_change_request', 'rule_change_approved', 'rule_change_rejected']
    reference_id: int
    title: str
    message: Optional[str]
    is_read: bool
    meta_data: Optional[Dict[str, Any]]
    created_at: datetime
    read_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    unread_count: int
    
    class Config:
        from_attributes = True

class UnreadCountResponse(BaseModel):
    unread_count: int
import asyncio
from datetime import datetime
import json
import logging
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from config.config_database import get_db
from schemas.common import SuccessResponse
from services.sse_notification import notification_service
from utils.auth import require_user
from schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse
)
from sqlalchemy.orm import Session
from services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

def custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)
    
@router.get("/stream")
async def compliance_notifications_stream(
    request: Request, 
    current_user = Depends(require_user())
):
    """SSE stream endpoint - gửi notifications cho user hiện tại"""
    
    logger = logging.getLogger(__name__)
    logger.info(f"User {current_user.username} (ID: {current_user.id}) connected to SSE")
    
    async def event_stream():
        client_queue = asyncio.Queue()
        
        try:
            # Add client với user_id
            await notification_service.add_client(current_user.id, client_queue)
            
            # Send connection confirmation
            yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE connected successfully', 'user_id': current_user.id})}\n\n"
            
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    # Process queued notifications
                    await notification_service.process_queued_notifications()
                    
                    # Wait for message with timeout
                    message = await asyncio.wait_for(client_queue.get(), timeout=5.0)
                    
                    # Send message to client
                    yield f"data: {json.dumps(message, default=custom_json_serializer)}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': str(asyncio.get_event_loop().time())})}\n\n"
                    
                except Exception as e:
                    logger.error(f"SSE streaming error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"SSE connection error: {e}")
        finally:
            await notification_service.remove_client(current_user.id, client_queue)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive", 
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.get("/list", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách notifications của user hiện tại
    
    ✅ FIXED: Trả về NotificationListResponse thay vì List[NotificationResponse]
    """
    service = NotificationService(db)
    
    # ✅ Method get_notifications đã trả về đúng NotificationListResponse
    return service.get_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit
    )

@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """Lấy số lượng notifications chưa đọc"""
    service = NotificationService(db)
    count = service.get_unread_count(current_user.id)
    return UnreadCountResponse(unread_count=count)

@router.patch("/{notification_id}/read", response_model=SuccessResponse)
async def mark_as_read(
    notification_id: int,
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """Đánh dấu notification đã đọc"""
    service = NotificationService(db)
    
    try:
        success = service.mark_as_read(notification_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return SuccessResponse(message="Notification marked as read")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/read-all", response_model=SuccessResponse)
async def mark_all_as_read(
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """Đánh dấu tất cả notifications là đã đọc"""
    service = NotificationService(db)
    
    try:
        count = service.mark_all_as_read(current_user.id)
        return SuccessResponse(message=f"Marked {count} notifications as read")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{notification_id}", response_model=SuccessResponse)
async def delete_notification(
    notification_id: int,
    current_user=Depends(require_user()),
    db: Session = Depends(get_db)
):
    """Xóa notification"""
    service = NotificationService(db)
    
    try:
        success = service.delete_notification(notification_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return SuccessResponse(message="Notification deleted")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
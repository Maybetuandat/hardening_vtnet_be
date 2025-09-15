
import asyncio
from datetime import datetime
import json
import logging
from decimal import Decimal
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from services.notification_service import notification_service
from utils.auth import require_user # Vẫn sử dụng require_user cũ

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

def custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)
    
@router.get("/stream")
async def compliance_notifications_stream(request: Request, current_user = Depends(require_user())):
    
    print("Debug Log: User connected to SSE stream", current_user.username, "at", datetime.utcnow())
    async def event_stream():
        client_queue = asyncio.Queue()
        
        try:
            await notification_service.add_client(client_queue)
            
            yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE connected successfully'})}\n\n"
            
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    await notification_service.process_queued_notifications()
                    
                    message = await asyncio.wait_for(client_queue.get(), timeout=5.0)
                    
                    yield f"data: {json.dumps(message, default=custom_json_serializer)}\n\n"
                    
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': str(asyncio.get_event_loop().time())})}\n\n"
                    
                except Exception as e:
                    logging.error(f"SSE streaming error: {e}")
                    break
                    
        except Exception as e:
            logging.error(f"SSE connection error: {e}")
        finally:
            await notification_service.remove_client(client_queue)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive", 
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )
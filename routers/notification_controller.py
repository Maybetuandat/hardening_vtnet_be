
import asyncio
import json
import logging
from decimal import Decimal
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from services.notification_service import notification_service

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

def custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
@router.get("/stream")
async def compliance_notifications_stream(request: Request):
    
    
    async def event_stream():
        client_queue = asyncio.Queue()
        
        try:
            # khi goi den url se thuc hien them client vao danh sach
            await notification_service.add_client(client_queue)
            
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE connected successfully'})}\n\n"
            
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    await notification_service.process_queued_notifications()
                    
                    
                    message = await asyncio.wait_for(client_queue.get(), timeout=5.0)
                    
                    
                    # function send data to frontend 
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
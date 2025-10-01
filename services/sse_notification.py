

import asyncio
import json
import logging
import queue
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SSENotificationService:
    def __init__(self):
        self._clients: Dict[int, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._notification_queue = queue.Queue()
    
    async def add_client(self, user_id: int, client_queue: asyncio.Queue):
        async with self._lock:
            if user_id not in self._clients:
                self._clients[user_id] = []
            self._clients[user_id].append(client_queue)
            total = sum(len(q) for q in self._clients.values())
            logger.info(f"User {user_id} connected. Total connections: {total}")
    
    async def remove_client(self, user_id: int, client_queue: asyncio.Queue):
        async with self._lock:
            if user_id in self._clients:
                try:
                    self._clients[user_id].remove(client_queue)
                    if not self._clients[user_id]:
                        del self._clients[user_id]
                except ValueError:
                    pass
            logger.info(f"User {user_id} disconnected")
    
    def notify_user(self, user_id: int, message: Dict):
        """Gửi notification cho 1 user cụ thể"""
        message['recipient_id'] = user_id
        self._notification_queue.put(message)
    
    def notify_users(self, user_ids: List[int], message: Dict):
        """Gửi notification cho nhiều users"""
        for user_id in user_ids:
            msg_copy = message.copy()
            msg_copy['recipient_id'] = user_id
            self._notification_queue.put(msg_copy)
    
    def broadcast_to_all(self, message: Dict):
        """Broadcast cho tất cả clients (fallback cho compliance scan cũ)"""
        message['recipient_id'] = None
        self._notification_queue.put(message)
    
    def notify_compliance_completed_sync(self, message: Dict):
        """Backward compatibility - deprecated, sử dụng notify_user hoặc broadcast_to_all"""
        self._notification_queue.put(message)
    
    async def process_queued_notifications(self):
        while True:
            try:
                message = self._notification_queue.get_nowait()
                recipient_id = message.get('recipient_id')
                
                if recipient_id is None:
                    await self._broadcast_to_all(message)
                else:
                    await self._send_to_user(recipient_id, message)
                
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
    
    async def _send_to_user(self, user_id: int, message: Dict):
        """Gửi message cho 1 user cụ thể"""
        async with self._lock:
            if user_id not in self._clients:
                logger.warning(f"User {user_id} not connected")
                return
            
            disconnected = []
            for client_queue in self._clients[user_id]:
                try:
                    await client_queue.put(message)
                except Exception as e:
                    logger.error(f"Failed to send to user {user_id}: {e}")
                    disconnected.append(client_queue)
            
            for queue in disconnected:
                try:
                    self._clients[user_id].remove(queue)
                except ValueError:
                    pass
            
            if not self._clients[user_id]:
                del self._clients[user_id]
            
            logger.info(f"Sent notification to user {user_id}")
    
    async def _broadcast_to_all(self, message: Dict):
        """Broadcast cho tất cả clients"""
        async with self._lock:
            total_sent = 0
            for user_id, queues in list(self._clients.items()):
                disconnected = []
                for client_queue in queues:
                    try:
                        await client_queue.put(message)
                        total_sent += 1
                    except Exception as e:
                        logger.error(f"Failed broadcast to user {user_id}: {e}")
                        disconnected.append(client_queue)
                
                for queue in disconnected:
                    try:
                        queues.remove(queue)
                    except ValueError:
                        pass
                
                if not queues:
                    del self._clients[user_id]
            
            logger.info(f"Broadcast sent to {total_sent} connections")

notification_service = SSENotificationService()
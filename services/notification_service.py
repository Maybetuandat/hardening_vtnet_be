# services/notification_service.py
import asyncio
import json
import logging
import threading
import queue
from typing import Dict, Set

class SSENotificationService:
    def __init__(self):
        self._clients: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        # Queue to store notifications from background threads
        self._notification_queue = queue.Queue()
    
    async def add_client(self, client_queue: asyncio.Queue):
        """Add a new client to receive notifications"""
        async with self._lock:
            self._clients.add(client_queue)
            logging.info(f"New SSE client connected. Total clients: {len(self._clients)}")
    
    async def remove_client(self, client_queue: asyncio.Queue):
        """Remove a client when disconnected"""
        async with self._lock:
            self._clients.discard(client_queue)
            logging.info(f"SSE client disconnected. Remaining clients: {len(self._clients)}")
    
    def notify_compliance_completed_sync(self, compliance_result_data: Dict):
        """Store notification in queue - called from background thread"""
        message = {
            "type": "compliance_completed",
            "data": compliance_result_data,
            "timestamp": compliance_result_data.get("updated_at")
        }
        
        # Put in queue - thread-safe
        self._notification_queue.put(message)
        logging.info(f"Queued notification for compliance {compliance_result_data.get('id')}")
    
    async def process_queued_notifications(self):
        """Process notifications from queue - called from FastAPI thread"""
        while True:
            try:
                # Non-blocking get
                message = self._notification_queue.get_nowait()
                
                if not self._clients:
                    continue
                
                # Send to all connected clients
                disconnected_clients = set()
                
                async with self._lock:
                    for client_queue in self._clients.copy():
                        try:
                            await client_queue.put(message)
                        except:
                            disconnected_clients.add(client_queue)
                    
                    # Clean up disconnected clients
                    for client in disconnected_clients:
                        self._clients.discard(client)
                
                print(f"Sent notification to {len(self._clients)} clients")
                
            except queue.Empty:
                # No messages to process
                break
            except Exception as e:
                logging.error(f"Error processing notification: {e}")

notification_service = SSENotificationService()
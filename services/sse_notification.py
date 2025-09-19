import asyncio
import json
import logging
import threading
import queue
from typing import Dict, Set

class SSENotificationService:
    def __init__(self):
        self._clients: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()   # su dung de khoa luong,dam bao khong bi xung doi khi co cac thao tac them/ xoa client trong nhieu corotine 
        self._notification_queue = queue.Queue()
    
    async def add_client(self, client_queue: asyncio.Queue):
        async with self._lock:
            self._clients.add(client_queue)
            logging.info(f"New SSE client connected. Total clients: {len(self._clients)}")
    
    async def remove_client(self, client_queue: asyncio.Queue):
        async with self._lock:
            self._clients.discard(client_queue)
            logging.info(f"SSE client disconnected. Remaining clients: {len(self._clients)}")
    
    def notify_compliance_completed_sync(self, message: Dict):
       
        
        self._notification_queue.put(message)
        
    
    async def process_queued_notifications(self):
        while True:
            try:
                message = self._notification_queue.get_nowait()
                
                if not self._clients:
                    continue
                
                disconnected_clients = set()
                
                async with self._lock:
                    for client_queue in self._clients.copy():
                        try:
                            await client_queue.put(message)
                        except:
                            disconnected_clients.add(client_queue)
                    
                    
                    for client in disconnected_clients:
                        self._clients.discard(client)
                
                print(f"Sent notification to {len(self._clients)} clients")
                
            except queue.Empty:
                
                break
            except Exception as e:
                logging.error(f"Error processing notification: {e}")

notification_service = SSENotificationService()
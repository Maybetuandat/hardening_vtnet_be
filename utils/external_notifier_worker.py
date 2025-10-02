import logging
import threading
import time
from typing import Optional
from queue import Queue, Empty

from client.external_notifier_client import ExternalNotifierClient
from config.external_notifier_config import ExternalNotifierConfig, get_external_notifier_config
from schemas.external_notifier_models import ExternalChatMessage, MessagePriority



logger = logging.getLogger(__name__)


class ExternalNotifierWorker:
    """
    Background worker for buffering and sending external notifications
    
    Features:
    - Thread-safe message buffering using Queue
    - Periodic flushing (configurable interval)
    - Graceful shutdown with message flush
    - Singleton pattern for single worker instance
    - Statistics tracking
    
    Usage:
        worker = ExternalNotifierWorker.get_instance()
        worker.start()
        worker.send_message(topic="test", title="Hello", message="World")
        worker.stop()
    """
    
    _instance: Optional['ExternalNotifierWorker'] = None
    _lock = threading.Lock()
    
    def __init__(self, config: Optional[ExternalNotifierConfig] = None):
        if not config:
            config = get_external_notifier_config()
        
        self.config = config
        self.buffer: Queue[ExternalChatMessage] = Queue()
        self.client: Optional[ExternalNotifierClient] = None
        
        # Threading
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False
        
        # Statistics
        self.stats = {
            'total_sent': 0,
            'total_failed': 0,
            'total_buffered': 0
        }
    
    @classmethod
    def get_instance(cls) -> 'ExternalNotifierWorker':
        """
        Get singleton instance (thread-safe)
        
        Returns:
            ExternalNotifierWorker: Singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def start(self):
        """
        Start the background worker thread
        
        Only starts if config is valid (enabled + all required fields set)
        """
       
        
        with self._lock:
            if self.is_running:
                logger.warning("⚠️ Worker already running")
                return
            
            self.client = ExternalNotifierClient(self.config)
            self.stop_event.clear()
            self.is_running = True
            
            self.worker_thread = threading.Thread(
                target=self._run_worker,
                name="ExternalNotifierWorker",
                daemon=True
            )
            self.worker_thread.start()
            
            logger.info(
                f"🚀 External notifier worker started "
                f"(interval={self.config.buffer_interval}s)"
            )
    
    def stop(self, timeout: float = 5.0):
        """
        Stop the worker gracefully
        
        Args:
            timeout: Max seconds to wait for worker to finish
        """
        if not self.is_running:
            return
        
        logger.info("🛑 Stopping external notifier worker...")
        
        self.stop_event.set()
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=timeout)
        
        # Flush remaining messages
        self._flush_buffer()
        
        if self.client:
            self.client.close()
        
        self.is_running = False
        logger.info("✅ External notifier worker stopped")
    
    def send_message(
        self,
        topic: str,
        title: str,
        message: str,
        priority: str = "normal",
        metadata: Optional[dict] = None
    ) -> bool:
     
     
        
      
        try:
           
            
            chat_message = ExternalChatMessage(
                topic=topic,
                title=title,
                message=message,
                priority=MessagePriority(priority),
                metadata=metadata or {}
            )
            
            self.buffer.put(chat_message, block=False)
            self.stats['total_buffered'] += 1
            
            logger.info(f"✅ Message buffered successfully: {chat_message}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error buffering message: {e}", exc_info=True)
            return False
    
    def _run_worker(self):
        """
        Main worker loop - runs in background thread
        
        Periodically flushes buffer based on configured interval
        """
        logger.info("🔄 Worker loop started")
        
        while not self.stop_event.is_set():
            try:
                # Wait for interval or stop signal
                self.stop_event.wait(timeout=self.config.buffer_interval)
                
                if not self.stop_event.is_set():
                    self._flush_buffer()
                    
            except Exception as e:
                logger.error(f"❌ Error in worker loop: {e}", exc_info=True)
                time.sleep(1)
        
        logger.info("🏁 Worker loop finished")
    
    def _flush_buffer(self):
        """
        Flush all messages in buffer
        
        Collects all queued messages and sends them via HTTP client
        """
        messages = []
        
        # Collect all messages from queue
        while True:
            try:
                message = self.buffer.get(block=False, timeout=0.1)
                messages.append(message)
            except Empty:
                break
        
        if not messages:
            return
        
        logger.info(f"📤 Flushing {len(messages)} messages...")
        
        # Send all messages
        success_count, failure_count = self.client.send_batch(messages)
        
        self.stats['total_sent'] += success_count
        self.stats['total_failed'] += failure_count
        
        logger.info(
            f"✅ Flush completed: {success_count} sent, {failure_count} failed. "
            f"Total stats: sent={self.stats['total_sent']}, "
            f"failed={self.stats['total_failed']}"
        )
    
    def get_stats(self) -> dict:
        """
        Get worker statistics
        
        Returns:
            dict: Statistics including sent/failed counts and status
        """
        return {
            **self.stats,
            'is_running': self.is_running,
            'buffer_size': self.buffer.qsize()
        }
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.is_running:
            self.stop()
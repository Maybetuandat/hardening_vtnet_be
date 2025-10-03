# utils/scan_listener_manager.py

import logging
import threading
from typing import Optional
from sqlalchemy.orm import Session

from config.config_database import get_db

from services.listen_scan_service import ScanResponseListener
from schemas.scan_message import ScanResponseMessage
from utils.redis_manager import get_pubsub_manager

logger = logging.getLogger(__name__)


class ScanListenerManager:
    """
    Manager để quản lý thread lắng nghe scan response từ Worker
    Chạy trong một thread riêng biệt, tách biệt với worker-service
    """
    
    _instance: Optional['ScanListenerManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        if ScanListenerManager._instance is not None:
            raise RuntimeError("Use get_instance() instead")
        
        self.pubsub_manager = get_pubsub_manager()
        self.listener_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False
        
        # Stats
        self.stats = {
            "total_responses_received": 0,
            "successful_saves": 0,
            "failed_saves": 0,
            "started_at": None,
            "last_response_at": None
        }
        
        logger.info("✅ ScanListenerManager initialized")
    
    @classmethod
    def get_instance(cls) -> 'ScanListenerManager':
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ScanListenerManager()
        return cls._instance
    
    def start(self):
        """Bắt đầu lắng nghe scan responses"""
        if self.is_running:
            logger.warning("⚠️ ScanListenerManager already running")
            return
        
        logger.info("🚀 Starting ScanListenerManager...")
        
        # Subscribe to scan response channel
        self.pubsub_manager.subscribe_scan_responses()
        
        self.is_running = True
        self.stop_event.clear()
        
        from datetime import datetime
        self.stats["started_at"] = datetime.now().isoformat()
        
        # Tạo thread để lắng nghe
        self.listener_thread = threading.Thread(
            target=self._listen_for_responses,
            daemon=True,
            name="ScanResponseListener"
        )
        self.listener_thread.start()
        
        logger.info("✅ ScanListenerManager started and listening for scan responses!")
    
    def stop(self, timeout=5):
        """Dừng listener"""
        if not self.is_running:
            logger.info("🛑 ScanListenerManager not running")
            return
        
        logger.info("🛑 Stopping ScanListenerManager...")
        self.stop_event.set()
        self.is_running = False
        
        if self.listener_thread:
            self.listener_thread.join(timeout=timeout)
        
        logger.info("✅ ScanListenerManager stopped")
    
    def _listen_for_responses(self):
        """Thread chính lắng nghe messages từ Redis"""
        logger.info("👂 Listening for scan responses from Worker...")
        
        try:
            for message_envelope in self.pubsub_manager.listen_for_messages():
                if self.stop_event.is_set():
                    logger.info("Stopping scan response listener as stop event is set")
                    break
                
                channel = message_envelope["channel"]
                message_payload = message_envelope["message"]
                
                # Chỉ xử lý scan_response channel
                if channel == self.pubsub_manager.settings.REDIS_CHANNEL_SCAN_RESPONSE:
                    self._handle_scan_response(message_payload)
                
        except Exception as e:
            logger.critical(f"❌ CRITICAL Error in scan response listener: {e}", exc_info=True)
    
    def _handle_scan_response(self, message_payload: dict):
        """Xử lý scan response message"""
        try:
            # Parse message
            message_type = message_payload.get("type")
            data = message_payload.get("data", {})
            
            if message_type != "scan_response":
                return
            
            # Convert to ScanResponseMessage
            scan_response = ScanResponseMessage(**data)
            
            self.stats["total_responses_received"] += 1
            
            logger.info(f"\n{'='*80}")
            logger.info(f"📨 RECEIVED SCAN RESPONSE FROM WORKER")
            logger.info(f"{'='*80}")
            logger.info(f"Scan Request ID: {scan_response.scan_request_id}")
            logger.info(f"Instance: {scan_response.instance_name} (ID: {scan_response.instance_id})")
            logger.info(f"Status: {scan_response.status}")
            logger.info(f"Rules: {scan_response.rules_passed}/{scan_response.total_rules} passed")
            logger.info(f"{'='*80}\n")
            
            # Lưu vào database - TẠO DB SESSION MỚI CHO MỖI REQUEST
            success = self._save_to_database(scan_response)
            
            if success:
                self.stats["successful_saves"] += 1
            else:
                self.stats["failed_saves"] += 1
            
            from datetime import datetime
            self.stats["last_response_at"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"❌ Error handling scan response: {e}", exc_info=True)
            self.stats["failed_saves"] += 1
    
    def _save_to_database(self, scan_response: ScanResponseMessage) -> bool:
        """
        Lưu scan response vào database
        QUAN TRỌNG: Tạo DB session mới cho mỗi request
        """
        db: Optional[Session] = None
        try:
            # Tạo DB session mới
            db = next(get_db())
            
            # Tạo listener service với DB session
            listener_service = ScanResponseListener(db)
            
            # Process và lưu
            success = listener_service.process_scan_response(scan_response)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error saving scan response to database: {e}", exc_info=True)
            if db:
                db.rollback()
            return False
        finally:
            # Đóng DB session
            if db:
                db.close()
    
    def get_stats(self) -> dict:
        """Lấy thống kê"""
        return self.stats.copy()
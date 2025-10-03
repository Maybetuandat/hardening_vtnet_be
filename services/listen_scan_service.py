import logging

from schemas.scan_message import ScanResponseMessage
from utils.redis_manager import get_pubsub_manager

logger = logging.getLogger(__name__)

class ScanResponseListener:
    def __init__(self, db_session):
        self.pubsub_manager = get_pubsub_manager()
        self.db = db_session  # inject DB session/service

    def start(self):
        """Subscribe và bắt đầu lắng nghe scan_response từ Worker"""
        self.pubsub_manager.subscribe_scan_responses()
        logger.info("📡 ScanResponseListener subscribed to worker scan_response channel")

        # Lắng nghe & gọi callback
        self.pubsub_manager.listen_for_messages(self._on_message)

    def _on_message(self, channel: str, message: dict):
        """Callback khi nhận được message từ Redis"""
        try:
            if message.get("type") != "scan_response":
                return  # bỏ qua loại message khác

            data = message["data"]
            response_msg = ScanResponseMessage(**data)
            logger.info(f"📥 Nhận scan_response cho instance {response_msg.instance_name}")

            # Lưu DB
            self._save_scan_result(response_msg)

        except Exception as e:
            logger.error(f"❌ Lỗi khi xử lý worker response: {e}", exc_info=True)

    def _save_scan_result(self, response: ScanResponseMessage):
        """Lưu kết quả scan vào DB"""
        try:
            record = {
                "scan_request_id": response.scan_request_id,
                "instance_id": response.instance_id,
                "status": response.status,
                "rules_passed": response.rules_passed,
                "rules_failed": response.rules_failed,
                "details": [r.dict() for r in response.rule_results]
            }
            self.db.insert_scan_result(record)  # gọi DAO/Repository
            logger.info(f"💾 Đã lưu kết quả scan {response.scan_request_id} vào DB")

        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu scan result vào DB: {e}", exc_info=True)

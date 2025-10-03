import logging
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from dao.compliance_result_dao import ComplianceDAO
from dao.rule_result_dao import RuleResultDAO
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
from schemas.scan_message import ScanResponseMessage
from utils.external_notifier_helper import send_external_notification

logger = logging.getLogger(__name__)


class ScanResponseListener:
    """Service lắng nghe và xử lý scan response từ Worker"""
    
    def __init__(self, db: Session):
        self.db = db
        self.compliance_dao = ComplianceDAO(db)
        self.rule_result_dao = RuleResultDAO(db)
    
    def process_scan_response(self, response: ScanResponseMessage) -> bool:
        """
        Xử lý scan response từ worker và lưu vào database
        
        Args:
            response: ScanResponseMessage nhận được từ worker
            
        Returns:
            bool: True nếu xử lý thành công
        """
        try:
            logger.info(f"📥 Processing scan response for instance {response.instance_name} (ID: {response.instance_id})")
            
            # 1. Tạo compliance result
            compliance_result = self._save_compliance_result(response)
            
            if not compliance_result:
                logger.error(f"❌ Failed to save compliance result for scan_request: {response.scan_request_id}")
                return False
            
            logger.info(f"✅ Saved compliance result with ID: {compliance_result.id}")
            
            # 2. Lưu rule results chi tiết
            if response.rule_results and len(response.rule_results) > 0:
                self._save_rule_results(compliance_result.id, response.rule_results)
                logger.info(f"✅ Saved {len(response.rule_results)} rule results")
            
            # 3. Gửi thông báo nếu scan failed hoặc có nhiều rules failed
            if response.status == "failed" or response.rules_failed > 0:
                self._send_scan_notification(response, compliance_result)
            
            logger.info(f"💾 Successfully processed scan response for {response.instance_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing scan response: {e}", exc_info=True)
            return False
    
    def _save_compliance_result(self, response: ScanResponseMessage) -> Optional[ComplianceResult]:
        """Lưu compliance result - CHỈ DÙNG CÁC FIELD CÓ TRONG MODEL"""
        try:
           
            
            # Tính score
            score = 0
            if response.total_rules > 0:
                score = round((response.rules_passed / response.total_rules) * 100, 2)
            
            # Tạo compliance result name
            # Format: "IP_ADDRESS - YYYY-MM-DD HH:MM:SS"
            compliance_name = f"{response.instance_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Tạo compliance result object
            # CHỈ DÙNG: name, instance_id, status, total_rules, passed_rules, failed_rules, score, detail_error
            compliance_result = ComplianceResult(
                name=compliance_name,
                instance_id=response.instance_id,
                status=response.status,
                total_rules=response.total_rules,
                passed_rules=response.rules_passed,
                failed_rules=response.rules_failed,
                score=score,
                detail_error=response.detail_error
            )
            
            # Lưu vào database
            created = self.compliance_dao.create(compliance_result)
            
            logger.info(f"✅ Created compliance result: ID={created.id}, Name={created.name}, Score={created.score}%")
            
            return created
            
        except Exception as e:
            logger.error(f"❌ Error saving compliance result: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def _save_rule_results(self, compliance_result_id: int, rule_results_data: list):
        """Lưu hàng loạt rule results"""
        try:
            rule_result_objects = []
            
            for result_data in rule_results_data:
                from datetime import datetime
                
                rule_result = RuleResult(
                    compliance_result_id=compliance_result_id,
                    rule_id=result_data.rule_id,
                    status=result_data.status,
                    message=result_data.message,
                    details_error=result_data.details_error,
                    output=result_data.output,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                rule_result_objects.append(rule_result)
            
            # Sử dụng DAO có sẵn để bulk create
            self.rule_result_dao.create_bulk(rule_result_objects)
            
            logger.info(f"✅ Bulk created {len(rule_result_objects)} rule results")
            
        except Exception as e:
            logger.error(f"❌ Error saving rule results: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    def _send_scan_notification(self, response: ScanResponseMessage, compliance_result: ComplianceResult):
        """Gửi thông báo khi scan có vấn đề"""
        try:
            if response.status == "failed":
                title = f"🔴 Scan Failed: {response.instance_name}"
                message = f"""
Instance: {response.instance_name} (ID: {response.instance_id})
Status: {response.status}
Error: {response.detail_error or 'Unknown error'}
Scan Request ID: {response.scan_request_id}
                """.strip()
                priority = "high"
            else:
                title = f"⚠️ Compliance Issues: {response.instance_name}"
                message = f"""
Instance: {response.instance_name} (ID: {response.instance_id})
Total Rules: {response.total_rules}
Passed: {response.rules_passed}
Failed: {response.rules_failed}
Score: {compliance_result.score}%
Scan Request ID: {response.scan_request_id}
                """.strip()
                priority = "normal"
            
            send_external_notification(
                topic="compliance_scan",
                title=title,
                message=message,
                priority=priority,
                metadata={
                    "scan_request_id": response.scan_request_id,
                    "instance_id": response.instance_id,
                    "compliance_result_id": compliance_result.id
                }
            )
            
            logger.info(f"📤 Sent notification for {response.instance_name}")
            
        except Exception as e:
            logger.error(f"❌ Error sending scan notification: {e}", exc_info=True)
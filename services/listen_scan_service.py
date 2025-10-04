import logging
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from dao.compliance_result_dao import ComplianceDAO
from dao.rule_result_dao import RuleResultDAO
from dao.instance_dao import InstanceDAO
from models import instance
from models.compliance_result import ComplianceResult
from models.instance import Instance
from models.rule_result import RuleResult
from schemas.scan_message import ScanResponseMessage
from schemas.compliance_result import ComplianceResultResponse
from services.sse_notification import sse_notification_service
from utils.external_notifier_helper import send_external_notification

logger = logging.getLogger(__name__)


class ScanResponseListener:
    """Service lắng nghe và xử lý scan response từ Worker"""
    
    def __init__(self, db: Session):
        self.db = db
        self.compliance_dao = ComplianceDAO(db)
        self.rule_result_dao = RuleResultDAO(db)
        self.instance_dao = InstanceDAO(db)
    
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
            
            # 3. Gửi thông báo external (Slack/Email) nếu có vấn đề
            if response.status == "failed" or response.rules_failed > 0:
                self._send_scan_notification(response, compliance_result)
            
            # 4. Gửi thông báo SSE đến frontend cho user
            self._notify_user_via_sse(response, compliance_result)
            
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
            
            
            instance = self.instance_dao.get_by_id(response.instance_id)

            status_scan = True if response.status == "completed" else False 
            if instance:
                if instance.status != status_scan:
                    instance.status = status_scan
                    self.instance_dao.update(instance)
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
        """Gửi thông báo external (Slack/Email) khi scan có vấn đề"""
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
            
            logger.info(f"📤 Sent external notification for {response.instance_name}")
            
        except Exception as e:
            logger.error(f"❌ Error sending scan notification: {e}", exc_info=True)
    
    def _notify_user_via_sse(self, response: ScanResponseMessage, compliance_result: ComplianceResult):
        """
        Gửi notification SSE đến frontend cho user sở hữu instance
        
        Được gọi sau khi scan hoàn tất để cập nhật UI real-time
        """
        try:
            # Lấy instance để biết user_id
            instance = self.instance_dao.get_by_id(response.instance_id)
            if not instance:
                logger.warning(f"⚠️ Instance {response.instance_id} not found, cannot notify via SSE")
                return
            
            # Lấy user_id từ instance
            user_id = instance.user_id
            if not user_id:
                logger.warning(f"⚠️ Instance {response.instance_id} has no owner, cannot notify via SSE")
                return
            
            # Tạo response object để gửi đến frontend
            compliance_response = self._convert_to_response(compliance_result, instance)
            
            # Tạo message theo format SSE
            message = {
                "type": compliance_result.status,  # "completed", "failed", etc.
                "data": compliance_response.dict(),
                "timestamp": compliance_result.updated_at.isoformat() if compliance_result.updated_at else datetime.now().isoformat()
            }
            
            # Gửi cho user cụ thể qua SSE
            sse_notification_service.notify_user(
                user_id=user_id,
                message=message
            )
            
            logger.info(f"✅ Sent SSE notification to user {user_id} for compliance scan '{compliance_result.status}' on instance {instance.name}")
            
        except Exception as e:
            logger.error(f"❌ Error sending SSE notification: {e}", exc_info=True)
    
    def _convert_to_response(self, compliance_result: ComplianceResult, instance: Instance) -> ComplianceResultResponse:
        """Convert ComplianceResult model sang ComplianceResultResponse schema"""
        # Lấy workload name nếu có
        workload_name = None
        if instance and hasattr(instance, 'workload') and instance.workload:
            workload_name = instance.workload.name
        
        return ComplianceResultResponse(
            id=compliance_result.id,
            name=compliance_result.name,
            instance_id=compliance_result.instance_id,
            instance_ip=instance.name if instance else "Unknown",
            status=compliance_result.status,
            total_rules=compliance_result.total_rules,
            passed_rules=compliance_result.passed_rules,
            failed_rules=compliance_result.failed_rules,
            score=round(compliance_result.score, 2),
            detail_error=compliance_result.detail_error,
            scan_date=compliance_result.scan_date if compliance_result.scan_date else datetime.now(),
            updated_at=compliance_result.updated_at if compliance_result.updated_at else datetime.now(),
            workload_name=workload_name
        )
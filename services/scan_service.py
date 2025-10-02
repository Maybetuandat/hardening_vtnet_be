import logging
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from dao.instance_dao import InstanceDAO
from dao.user_dao import UserDAO
from models.user import User
from models.instance import Instance
from schemas.compliance_result import ComplianceScanRequest, ComplianceScanResponse
from schemas.scan_message import ScanInstanceMessage, RuleInfo, InstanceCredentials
from utils.redis_manager import get_pubsub_manager


logger = logging.getLogger(__name__)


class ScanService:
    
    def __init__(self, db: Session):
        self.db = db
        self.instance_dao = InstanceDAO(db)
        self.user_dao = UserDAO(db)
        self.pubsub_manager = get_pubsub_manager()
    
    def start_compliance_scan(
        self, 
        scan_request: ComplianceScanRequest, 
        current_user: User
    ) -> ComplianceScanResponse:
       
        try:
            scan_request_id = str(uuid.uuid4())
            
         
            
            if scan_request.server_ids:
                
                return self._publish_specific_servers_to_queue(
                    scan_request.server_ids,
                    scan_request_id,
                    current_user
                )
            else:
                
                return self._publish_all_servers_to_queue(
                    scan_request_id,
                    current_user
                )
                
        except Exception as e:
            logger.error(f"❌ Error starting compliance scan: {str(e)}")
            raise e
    
    def _publish_specific_servers_to_queue(
        self,
        server_ids: List[int],
        scan_request_id: str,
        current_user: User
    ) -> ComplianceScanResponse:
        try:
            # Sử dụng DAO để get instances với eager loading
            instances = self.instance_dao.get_instances_with_relationships_by_ids(
                instance_ids=server_ids,
                status=True,
                has_workload=True,
                  current_user=current_user
            )
            
            if not instances:
                logger.warning(f"⚠️ No valid instances found for IDs: {server_ids}")
                return ComplianceScanResponse(
                    message="Không tìm thấy instances hợp lệ để scan",
                    total_instances=0,
                    started_scans=[]
                )
            
            published_ids = []
            skipped_count = 0
            
            for instance in instances:
                try:
                    # Kiểm tra workload và rules
                    if not instance.workload:
                        logger.warning(f"⚠️ Instance {instance.name} has no workload, skipping")
                        skipped_count += 1
                        continue
                    
                    if not instance.workload.rules:
                        logger.warning(f"⚠️ Instance {instance.name} workload has no rules, skipping")
                        skipped_count += 1
                        continue
                    
                    # Tạo message và convert sang dict với JSON serializable
                    message = self._create_scan_message(instance, scan_request_id)
                    message_dict = self._convert_to_json_serializable(message.dict())
                    
                    # Publish vào Redis
                    self.pubsub_manager.publish_scan_request(message_dict)
                    
                    published_ids.append(instance.id)
                    logger.info(f"✅ Published instance {instance.name} (ID: {instance.id}) to queue")
                    
                except Exception as e:
                    logger.error(f"❌ Error publishing instance {instance.id}: {e}")
                    skipped_count += 1
            
            message = f"Đã đẩy {len(published_ids)} instances vào scan queue"
            if skipped_count > 0:
                message += f" ({skipped_count} instances bị bỏ qua)"
            
            logger.info(f"📊 Scan completed: {len(published_ids)} published, {skipped_count} skipped")
            
            return ComplianceScanResponse(
                message=message,
                total_instances=len(instances),
                started_scans=published_ids
            )
            
        except Exception as e:
            logger.error(f"❌ Error in _publish_specific_servers_to_queue: {e}")
            raise
    
    def _publish_all_servers_to_queue(
        self,
        scan_request_id: str,
        current_user: User
    ) -> ComplianceScanResponse:
        """Publish TẤT CẢ servers có workload vào Redis queue"""
        try:
            # Sử dụng DAO để get all instances với eager loading
            instances = self.instance_dao.get_instances_with_relationships(
                status=True,
                has_workload=True
            )
            
            if not instances:
                logger.warning("⚠️ No instances with workload found")
                return ComplianceScanResponse(
                    message="Không có instances nào có workload để scan",
                    total_instances=0,
                    started_scans=[]
                )
            
            logger.info(f"📊 Found {len(instances)} instances with workload")
            
            published_ids = []
            skipped_count = 0
            
            for instance in instances:
                try:
                    # Kiểm tra workload và rules
                    if not instance.workload:
                        logger.warning(f"⚠️ Instance {instance.name} has no workload, skipping")
                        skipped_count += 1
                        continue
                    
                    if not instance.workload.rules:
                        logger.warning(f"⚠️ Instance {instance.name} workload has no rules, skipping")
                        skipped_count += 1
                        continue
                    
                    # Tạo message và convert sang dict với JSON serializable
                    message = self._create_scan_message(instance, scan_request_id)
                    message_dict = self._convert_to_json_serializable(message.dict())
                    
                    # Publish vào Redis
                    self.pubsub_manager.publish_scan_request(message_dict)
                    
                    published_ids.append(instance.id)
                    logger.info(f"✅ Published instance {instance.name} (ID: {instance.id}) to queue")
                    
                except Exception as e:
                    logger.error(f"❌ Error publishing instance {instance.id}: {e}")
                    skipped_count += 1
            
            message = f"Đã đẩy {len(published_ids)} instances vào scan queue"
            if skipped_count > 0:
                message += f" ({skipped_count} instances bị bỏ qua)"
            
            logger.info(f"📊 Scan completed: {len(published_ids)} published, {skipped_count} skipped")
            
            return ComplianceScanResponse(
                message=message,
                total_instances=len(instances),
                started_scans=published_ids
            )
            
        except Exception as e:
            logger.error(f"❌ Error in _publish_all_servers_to_queue: {e}")
            raise
    
    def _create_scan_message(self, instance: Instance, scan_request_id: str) -> ScanInstanceMessage:
        """
        Tạo message object HOÀN CHỈNH
        CREDENTIALS LẤY TỪ USER (instance.user)
        """
        
        # Extract rules info - chỉ lấy rules active
        rules_info = [
            RuleInfo(
                id=rule.id,
                name=rule.name,
                command=rule.command,
                parameters=rule.parameters
            )
            for rule in instance.workload.rules
            if rule.is_active == "active"
        ]
        
        # LẤY CREDENTIALS TỪ USER
        credentials = InstanceCredentials(
            username=instance.user.username if hasattr(instance.user, 'username') else None,
            password=instance.user.ssh_password if hasattr(instance.user, 'ssh_password') else None
        )
        
        return ScanInstanceMessage(
            # Instance info
            instance_id=instance.id,
            instance_name=instance.name,
            ssh_port=instance.ssh_port,
            instance_role=instance.instance_role,
            
            # Workload info
            workload_id=instance.workload.id,
            workload_name=instance.workload.name,
            workload_description=instance.workload.description,
            
            # OS info
            os_id=instance.os.id,
            os_name=instance.os.name,
            os_type=instance.os.type,
            os_display=instance.os.display,
            
            # User info
            user_id=instance.user_id,
            
            # Rules
            rules=rules_info,
            
            # CREDENTIALS TỪ USER
            credentials=credentials,
            
            # Metadata
            scan_request_id=scan_request_id
        )
    
    def _convert_to_json_serializable(self, data):
        """
        Convert tất cả datetime objects sang ISO format string để JSON serializable
        """
        if isinstance(data, dict):
            return {key: self._convert_to_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_to_json_serializable(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()  # Convert datetime to ISO string
        else:
            return data
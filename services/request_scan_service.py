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
from services.listen_scan_service import ScanResponseListener
from utils.redis_manager import get_pubsub_manager





class ScanService:
    
    def __init__(self, db: Session):
        self.db = db
        self.instance_dao = InstanceDAO(db)
        self.user_dao = UserDAO(db)
        self.pubsub_manager = get_pubsub_manager()
        self.scan_result_listener = ScanResponseListener(db)
    
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
                has_workload=True,
                current_user=current_user
            )

            print("Debug server_ids:", server_ids)
            if not instances:
                print("Debug: No valid instances found for the provided server IDs.")
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
                        
                        skipped_count += 1
                        continue
                    
                    if not instance.workload.rules:
                        
                        skipped_count += 1
                        continue
                    
                    # Tạo message và convert sang dict với JSON serializable
                    message = self._create_scan_message(instance, scan_request_id)
                    message_dict = self._convert_to_json_serializable(message.dict())
                    
                    # Publish vào Redis
                    self.pubsub_manager.publish_scan_request(message_dict)
                    
                    published_ids.append(instance.id)
                    
                    
                except Exception as e:
                    
                    skipped_count += 1
            
            message = f"Đã đẩy {len(published_ids)} instances vào scan queue"
            if skipped_count > 0:
                message += f" ({skipped_count} instances bị bỏ qua)"
            
            
            
            return ComplianceScanResponse(
                message=message,
                total_instances=len(instances),
                started_scans=published_ids
            )
            
        except Exception as e:
            
            raise
    
    def _publish_all_servers_to_queue(
        self,
        scan_request_id: str,
        current_user: User
    ) -> ComplianceScanResponse:
        try:
            instances = self.instance_dao.get_instances_with_relationships(
                has_workload=True
            )
            
            if not instances:
                
                return ComplianceScanResponse(
                    message="Không có instances nào có workload để scan",
                    total_instances=0,
                    started_scans=[]
                )

            

            published_ids = []
            skipped_count = 0
            
            for instance in instances:
                try:
                    # Kiểm tra workload và rules
                    if not instance.workload:
                        
                        skipped_count += 1
                        continue
                    
                    if not instance.workload.rules:
                        
                        skipped_count += 1
                        continue
                    
                    # Tạo message và convert sang dict với JSON serializable
                    message = self._create_scan_message(instance, scan_request_id)
                    message_dict = self._convert_to_json_serializable(message.dict())
                    
                    # Publish vào Redis
                    self.pubsub_manager.publish_scan_request(message_dict)
                    
                    published_ids.append(instance.id)


                except Exception as e:
                    
                    skipped_count += 1
            
            message = f"Đã đẩy {len(published_ids)} instances vào scan queue"
            if skipped_count > 0:
                message += f" ({skipped_count} instances bị bỏ qua)"
            
            
            
            return ComplianceScanResponse(
                message=message,
                total_instances=len(instances),
                started_scans=published_ids
            )
            
        except Exception as e:
            
            raise
    
    def _create_scan_message(self, instance: Instance, scan_request_id: str) -> ScanInstanceMessage:
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
        
    
        credentials = InstanceCredentials(
            username=instance.user.username if hasattr(instance.user, 'username') else None,
            password=instance.user.ssh_password if hasattr(instance.user, 'ssh_password') else None
        )
        
        return ScanInstanceMessage(
         
            instance_id=instance.id,
            instance_name=instance.name,
            ssh_port=instance.ssh_port,
            instance_role=instance.instance_role,
            
          
            workload_id=instance.workload.id,
            workload_name=instance.workload.name,
            workload_description=instance.workload.description,
            
         
            os_id=instance.os.id,
            os_name=instance.os.name,
            os_type=instance.os.type,
            os_display=instance.os.display,
            
          
            user_id=instance.user_id,
            
           
            rules=rules_info,
            
         
            credentials=credentials,
            
          
            scan_request_id=scan_request_id
        )
    
    def _convert_to_json_serializable(self, data):
        if isinstance(data, dict):
            return {key: self._convert_to_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_to_json_serializable(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()  # Convert datetime to ISO string
        else:
            return data
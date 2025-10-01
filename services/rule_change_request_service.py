# services/rule_change_request_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from dao.rule_change_request_dao import RuleChangeRequestDAO
from dao.notification_dao import NotificationDAO
from dao.user_dao import UserDAO
from dao.workload_dao import WorkLoadDAO
from dao.rule_dao import RuleDAO
from models.rule_change_request import RuleChangeRequest
from models.notification import Notification
from models.rule import Rule
from schemas.rule_change_request import (
    RuleChangeRequestCreate,
    RuleChangeRequestUpdate,
    RuleChangeRequestResponse
)
from services.sse_notification import notification_service

logger = logging.getLogger(__name__)

class RuleChangeRequestService:
    """Service xử lý logic cho RuleChangeRequest"""
    
    def __init__(self, db: Session):
        self.db = db
        self.request_dao = RuleChangeRequestDAO(db)
        self.notification_dao = NotificationDAO(db)
        self.user_dao = UserDAO(db)
        self.workload_dao = WorkLoadDAO(db)
        self.rule_dao = RuleDAO(db)
    
    # ===== CREATE REQUEST =====
    
    def create_update_request(
        self, 
        rule_id: int,
        new_rule_data: Dict[str, Any],
        current_user
    ) -> RuleChangeRequestResponse:
        """
        User tạo request UPDATE rule
        
        Flow:
        1. Validate rule exists
        2. Check không có pending request cho rule này
        3. Lưu old_value (rule hiện tại) và new_value (data mới)
        4. Tạo RuleChangeRequest
        5. Notify tất cả admin
        """
        try:
            # Step 1: Get existing rule
            existing_rule = self.rule_dao.get_by_id(rule_id)
            if not existing_rule:
                raise ValueError(f"Rule ID {rule_id} not found")
            
            # Step 2: Check pending request
            if self.request_dao.has_pending_request_for_rule(rule_id):
                raise ValueError("This rule already has a pending change request. Please wait for admin approval.")
            
            # Step 3: Prepare old_value (current rule data)
            old_value = self._rule_to_dict(existing_rule)
            
            # Step 4: Prepare new_value (merge current + changes)
            new_value = old_value.copy()
            new_value.update(new_rule_data)
            
            # Step 5: Create RuleChangeRequest
            request = RuleChangeRequest(
                workload_id=existing_rule.workload_id,
                rule_id=rule_id,
                user_id=current_user.id,
                request_type='update',
                old_value=old_value,
                new_value=new_value,
                status='pending'
            )
            
            created_request = self.request_dao.create(request)
            
            # Step 6: Notify admins
            self._notify_admins_about_new_request(created_request, current_user)
            
            logger.info(f"✅ User {current_user.username} created UPDATE request for rule {rule_id}")
            
            return self._convert_to_response(created_request)
            
        except ValueError as e:
            logger.error(f"❌ Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error creating update request: {e}")
            raise Exception(f"Failed to create update request: {str(e)}")
    
    def create_new_rule_request(
        self,
        workload_id: int,
        new_rule_data: Dict[str, Any],
        current_user
    ) -> RuleChangeRequestResponse:
        """
        User tạo request CREATE rule mới
        
        Flow:
        1. Validate workload exists
        2. Tạo RuleChangeRequest với old_value=None
        3. Notify tất cả admin
        """
        try:
            # Step 1: Validate workload
            workload = self.workload_dao.get_by_id(workload_id)
            if not workload:
                raise ValueError(f"Workload ID {workload_id} not found")
            
            # Step 2: Prepare new_value
            new_value = {
                "name": new_rule_data.get("name"),
                "description": new_rule_data.get("description"),
                "command": new_rule_data.get("command"),
                "parameters": new_rule_data.get("parameters"),
                "suggested_fix": new_rule_data.get("suggested_fix"),
                "workload_id": workload_id,
                "is_active": new_rule_data.get("is_active", "active")
            }
            
            # Step 3: Create RuleChangeRequest
            request = RuleChangeRequest(
                workload_id=workload_id,
                rule_id=None,  # No rule_id for CREATE
                user_id=current_user.id,
                request_type='create',
                old_value=None,  # No old value for CREATE
                new_value=new_value,
                status='pending'
            )
            
            created_request = self.request_dao.create(request)
            
            # Step 4: Notify admins
            self._notify_admins_about_new_request(created_request, current_user)
            
            logger.info(f"✅ User {current_user.username} created CREATE request for workload {workload_id}")
            
            return self._convert_to_response(created_request)
            
        except ValueError as e:
            logger.error(f"❌ Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error creating new rule request: {e}")
            raise Exception(f"Failed to create new rule request: {str(e)}")
    
    # ===== ADMIN APPROVE/REJECT =====
    
    def approve_request(
        self,
        request_id: int,
        admin_user,
        admin_note: Optional[str] = None
    ) -> RuleChangeRequestResponse:
        """
        Admin approve request
        
        Flow:
        1. Get request
        2. Validate status = pending
        3. Apply changes:
           - CREATE: Tạo rule mới
           - UPDATE: Update rule hiện tại
        4. Update request status = approved
        5. Notify user về kết quả
        """
        try:
            # Step 1: Get request
            request = self.request_dao.get_by_id(request_id)
            if not request:
                raise ValueError(f"Request ID {request_id} not found")
            
            # Step 2: Validate status
            if request.status != 'pending':
                raise ValueError(f"Cannot approve request with status: {request.status}")
            
            # Step 3: Apply changes
            if request.request_type == 'create':
                self._apply_create_request(request)
            elif request.request_type == 'update':
                self._apply_update_request(request)
            else:
                raise ValueError(f"Unknown request type: {request.request_type}")
            
            # Step 4: Update request
            request.status = 'approved'
            request.admin_id = admin_user.id
            request.admin_note = admin_note
            request.processed_at = datetime.utcnow()
            
            updated_request = self.request_dao.update(request)
            
            # Step 5: Notify user
            self._notify_user_about_result(updated_request, admin_user, 'approved')
            
            logger.info(f"✅ Admin {admin_user.username} approved request {request_id}")
            
            return self._convert_to_response(updated_request)
            
        except ValueError as e:
            logger.error(f"❌ Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error approving request: {e}")
            raise Exception(f"Failed to approve request: {str(e)}")
    
    def reject_request(
        self,
        request_id: int,
        admin_user,
        admin_note: Optional[str] = None
    ) -> RuleChangeRequestResponse:
        """
        Admin reject request
        
        Flow:
        1. Get request
        2. Validate status = pending
        3. Update request status = rejected
        4. Notify user về kết quả
        """
        try:
            # Step 1: Get request
            request = self.request_dao.get_by_id(request_id)
            if not request:
                raise ValueError(f"Request ID {request_id} not found")
            
            # Step 2: Validate status
            if request.status != 'pending':
                raise ValueError(f"Cannot reject request with status: {request.status}")
            
            # Step 3: Update request
            request.status = 'rejected'
            request.admin_id = admin_user.id
            request.admin_note = admin_note or "Request rejected by admin"
            request.processed_at = datetime.utcnow()
            
            updated_request = self.request_dao.update(request)
            
            # Step 4: Notify user
            self._notify_user_about_result(updated_request, admin_user, 'rejected')
            
            logger.info(f"✅ Admin {admin_user.username} rejected request {request_id}")
            
            return self._convert_to_response(updated_request)
            
        except ValueError as e:
            logger.error(f"❌ Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error rejecting request: {e}")
            raise Exception(f"Failed to reject request: {str(e)}")
    
    # ===== QUERY METHODS =====
    
    def get_request_by_id(self, request_id: int) -> Optional[RuleChangeRequestResponse]:
        """Lấy chi tiết 1 request"""
        request = self.request_dao.get_by_id(request_id)
        if request:
            return self._convert_to_response(request)
        return None
    
    def get_all_pending_requests(self) -> List[RuleChangeRequestResponse]:
        """Admin lấy tất cả pending requests"""
        requests = self.request_dao.get_all_pending()
        return [self._convert_to_response(r) for r in requests]
    
    def get_user_requests(self, user_id: int) -> List[RuleChangeRequestResponse]:
        """User xem lịch sử requests của mình"""
        requests = self.request_dao.get_by_user(user_id)
        return [self._convert_to_response(r) for r in requests]
    
    def get_workload_requests(
        self, 
        workload_id: int,
        status: Optional[str] = None
    ) -> List[RuleChangeRequestResponse]:
        """Lấy requests theo workload"""
        requests = self.request_dao.get_by_workload(workload_id, status)
        return [self._convert_to_response(r) for r in requests]
    
    def count_pending_requests(self) -> int:
        """Đếm tổng số pending requests"""
        return self.request_dao.count_pending_requests()
    
    # ===== PRIVATE HELPER METHODS =====
    
    def _apply_create_request(self, request: RuleChangeRequest):
        """Apply CREATE request: Tạo rule mới"""
        try:
            new_value = request.new_value
            
            new_rule = Rule(
                name=new_value.get("name"),
                description=new_value.get("description"),
                command=new_value.get("command"),
                parameters=new_value.get("parameters"),
                suggested_fix=new_value.get("suggested_fix"),
                workload_id=request.workload_id,
                is_active=new_value.get("is_active", "active"),
                role_can_request_edit="admin",  # Default
                can_be_copied=True
            )
            
            created_rule = self.rule_dao.create(new_rule)
            logger.info(f"✅ Created new rule ID {created_rule.id} from request {request.id}")
            
        except Exception as e:
            logger.error(f"❌ Error applying CREATE request: {e}")
            raise
    
    def _apply_update_request(self, request: RuleChangeRequest):
        """Apply UPDATE request: Cập nhật rule hiện tại"""
        try:
            rule = self.rule_dao.get_by_id(request.rule_id)
            if not rule:
                raise ValueError(f"Rule ID {request.rule_id} not found")
            
            new_value = request.new_value
            
            # Update fields
            rule.name = new_value.get("name", rule.name)
            rule.description = new_value.get("description", rule.description)
            rule.command = new_value.get("command", rule.command)
            rule.parameters = new_value.get("parameters", rule.parameters)
            rule.suggested_fix = new_value.get("suggested_fix", rule.suggested_fix)
            rule.is_active = new_value.get("is_active", rule.is_active)
            
            updated_rule = self.rule_dao.update(rule)
            logger.info(f"✅ Updated rule ID {updated_rule.id} from request {request.id}")
            
        except Exception as e:
            logger.error(f"❌ Error applying UPDATE request: {e}")
            raise
    
    def _notify_admins_about_new_request(self, request: RuleChangeRequest, requester_user):
        """Tạo notifications cho tất cả admin khi có request mới"""
        try:
            # Get all admin users
            admin_users = self.user_dao.get_users_by_role('admin')
            if not admin_users:
                logger.warning("⚠️ No admin users found to notify")
                return
            
            # Get workload info
            workload = self.workload_dao.get_by_id(request.workload_id)
            workload_name = workload.name if workload else "Unknown Workload"
            
            # Get rule name (if update)
            rule_name = "New Rule"
            if request.rule_id:
                rule = self.rule_dao.get_by_id(request.rule_id)
                rule_name = rule.name if rule else f"Rule #{request.rule_id}"
            
            # Prepare notification content
            action = "create" if request.request_type == 'create' else "update"
            title = f"🔄 New Rule {action.title()} Request"
            message = f"{requester_user.username} requests to {action} rule '{rule_name}' in workload '{workload_name}'"
            
            metadata = {
                "request_id": request.id,
                "rule_id": request.rule_id,
                "rule_name": rule_name,
                "workload_id": request.workload_id,
                "workload_name": workload_name,
                "requester_id": requester_user.id,
                "requester_username": requester_user.username,
                "request_type": request.request_type
            }
            
            # Create notifications for all admins
            notifications = []
            for admin in admin_users:
                notification = Notification(
                    recipient_id=admin.id,
                    type="rule_change_request",
                    reference_id=request.id,
                    title=title,
                    message=message,
                    is_read=False,
                    metadata=metadata
                )
                notifications.append(notification)
            
            created_notifications = self.notification_dao.create_batch(notifications)
            
            # Push via SSE to all admins
            for notif in created_notifications:
                notification_service.notify_compliance_completed_sync({
                    "type": "rule_change_request",
                    "notification_id": notif.id,
                    "title": title,
                    "message": message,
                    "metadata": metadata,
                    "timestamp": notif.created_at.isoformat()
                })
            
            logger.info(f"✅ Notified {len(admin_users)} admins about new request {request.id}")
            
        except Exception as e:
            logger.error(f"❌ Error notifying admins: {e}")
            # Don't fail the whole operation if notification fails
    
    def _notify_user_about_result(
        self, 
        request: RuleChangeRequest, 
        admin_user,
        result: str  # 'approved' or 'rejected'
    ):
        """Notify user về kết quả approve/reject"""
        try:
            requester = self.user_dao.get_by_id(request.user_id)
            if not requester:
                logger.warning(f"⚠️ Requester user {request.user_id} not found")
                return
            
            # Get workload info
            workload = self.workload_dao.get_by_id(request.workload_id)
            workload_name = workload.name if workload else "Unknown Workload"
            
            # Get rule name
            rule_name = "New Rule"
            if request.rule_id:
                rule = self.rule_dao.get_by_id(request.rule_id)
                rule_name = rule.name if rule else f"Rule #{request.rule_id}"
            
            # Prepare notification content
            if result == 'approved':
                icon = "✅"
                title = f"{icon} Rule Change Request Approved"
                message = f"Admin {admin_user.username} approved your request to {request.request_type} rule '{rule_name}' in workload '{workload_name}'"
            else:  # rejected
                icon = "❌"
                title = f"{icon} Rule Change Request Rejected"
                message = f"Admin {admin_user.username} rejected your request to {request.request_type} rule '{rule_name}' in workload '{workload_name}'"
                if request.admin_note:
                    message += f"\nReason: {request.admin_note}"
            
            metadata = {
                "request_id": request.id,
                "rule_id": request.rule_id,
                "rule_name": rule_name,
                "workload_id": request.workload_id,
                "workload_name": workload_name,
                "admin_id": admin_user.id,
                "admin_username": admin_user.username,
                "request_type": request.request_type,
                "result": result,
                "admin_note": request.admin_note
            }
            
            # Create notification
            notification = Notification(
                recipient_id=requester.id,
                type=f"rule_change_{result}",
                reference_id=request.id,
                title=title,
                message=message,
                is_read=False,
                metadata=metadata
            )
            
            created_notification = self.notification_dao.create(notification)
            
            # Push via SSE
            notification_service.notify_compliance_completed_sync({
                "type": f"rule_change_{result}",
                "notification_id": created_notification.id,
                "title": title,
                "message": message,
                "metadata": metadata,
                "timestamp": created_notification.created_at.isoformat()
            })
            
            logger.info(f"✅ Notified user {requester.username} about request {request.id} result: {result}")
            
        except Exception as e:
            logger.error(f"❌ Error notifying user: {e}")
    
    def _rule_to_dict(self, rule: Rule) -> Dict[str, Any]:
        """Convert Rule model to dict for JSON storage"""
        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "command": rule.command,
            "parameters": rule.parameters,
            "suggested_fix": rule.suggested_fix,
            "workload_id": rule.workload_id,
            "is_active": rule.is_active,
            "role_can_request_edit": rule.role_can_request_edit,
            "copied_from_id": rule.copied_from_id,
            "can_be_copied": rule.can_be_copied,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
        }
    
    def _convert_to_response(self, request: RuleChangeRequest) -> RuleChangeRequestResponse:
        """Convert model to response DTO"""
        response_data = {
            "id": request.id,
            "workload_id": request.workload_id,
            "rule_id": request.rule_id,
            "user_id": request.user_id,
            "request_type": request.request_type,
            "old_value": request.old_value,
            "new_value": request.new_value,
            "status": request.status,
            "admin_id": request.admin_id,
            "admin_note": request.admin_note,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
            "processed_at": request.processed_at
        }
        
        # Add extra info from relationships
        if request.workload:
            response_data["workload_name"] = request.workload.name
        
        if request.rule:
            response_data["rule_name"] = request.rule.name
        
        if request.requester:
            response_data["requester_username"] = request.requester.username
        
        if request.admin:
            response_data["admin_username"] = request.admin.username
        
        return RuleChangeRequestResponse(**response_data)
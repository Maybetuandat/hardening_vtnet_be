# services/fix_request_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from dao.fix_request_dao import FixRequestDAO
from models.fix_request import FixRequest
from models.user import User
from schemas.fix_execution import ServerFixResponse
from schemas.fix_request import (
    FixRequestCreate,
    FixRequestResponse,
    FixRequestApprove
)
from services.fix_service import FixService

logger = logging.getLogger(__name__)


class FixRequestService:
    """Service xử lý logic cho Fix Request"""
    
    def __init__(self, db: Session):
        self.db = db
        self.fix_request_dao = FixRequestDAO(db)
        self.fix_service = FixService(db)
    
    def create_fix_request(
        self,
        data: FixRequestCreate,
        current_user: User
    ) -> FixRequestResponse:
        """
        Tạo fix request mới
        """
        try:
            # Kiểm tra xem rule result đã có pending request chưa
            if self.fix_request_dao.has_pending_request_for_rule_result(data.rule_result_id):
                raise ValueError("Rule result này đã có fix request đang chờ xử lý")
            
            # Tạo fix request mới
            fix_request = FixRequest(
                rule_result_id=data.rule_result_id,
                instance_id=data.instance_id,
                title=data.title,
                description=data.description,
                status="pending",
                created_by=current_user.username,
                created_at=datetime.utcnow()
            )
            
            created_request = self.fix_request_dao.create(fix_request)
            logger.info(f"✅ Created fix request ID {created_request.id} by user {current_user.username}")
            
            # TODO: Gửi notification cho admin
            
            return self._convert_to_response(created_request)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"❌ Error creating fix request: {e}")
            raise Exception(f"Lỗi khi tạo fix request: {str(e)}")
    
    def approve_request(
        self,
        request_id: int,
        admin_user: User,
        admin_comment: Optional[str] = None
    ) -> FixRequestResponse:
        """
        Admin approve fix request và thực thi
        """
        try:
            fix_request = self.fix_request_dao.get_by_id(request_id)
            print("Debug fix request:", fix_request)
            
            if not fix_request:
                raise ValueError(f"Fix request ID {request_id} không tồn tại")
            
            if fix_request.status != "pending":
                raise ValueError(f"Fix request này đã được xử lý (status: {fix_request.status})")
            
            # Cập nhật trạng thái approved
            fix_request.status = "approved"
            fix_request.admin_id = admin_user.id
            fix_request.approved_at = datetime.utcnow()
            fix_request.admin_comment = admin_comment
            
            updated_request = self.fix_request_dao.update(fix_request)
            logger.info(f"✅ Admin {admin_user.username} approved fix request ID {request_id}")
            
            ServerFixResponse = self.fix_service.fix_request_from_admin(request_id)
            
            return self._convert_to_response(updated_request)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"❌ Error approving fix request: {e}")
            raise Exception(f"Lỗi khi approve fix request: {str(e)}")
    
    def reject_request(
        self,
        request_id: int,
        admin_user: User,
        admin_comment: Optional[str] = None
    ) -> FixRequestResponse:
        """
        Admin reject fix request
        """
        try:
            fix_request = self.fix_request_dao.get_by_id(request_id)
            
            if not fix_request:
                raise ValueError(f"Fix request ID {request_id} không tồn tại")
            
            if fix_request.status != "pending":
                raise ValueError(f"Fix request này đã được xử lý (status: {fix_request.status})")
            
            # Cập nhật trạng thái rejected
            fix_request.status = "rejected"
            fix_request.admin_id = admin_user.id
            fix_request.approved_at = datetime.utcnow()
            fix_request.admin_comment = admin_comment
            
            updated_request = self.fix_request_dao.update(fix_request)
            logger.info(f"✅ Admin {admin_user.username} rejected fix request ID {request_id}")
            
            # TODO: Gửi notification cho user tạo request
            
            return self._convert_to_response(updated_request)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"❌ Error rejecting fix request: {e}")
            raise Exception(f"Lỗi khi reject fix request: {str(e)}")
    
    def get_all_requests(self, status: Optional[str] = None) -> List[FixRequestResponse]:
        """
        Lấy tất cả fix requests (cho admin)
        """
        try:
            requests = self.fix_request_dao.get_all(status)
            return [self._convert_to_response(req) for req in requests]
        except Exception as e:
            logger.error(f"❌ Error getting all requests: {e}")
            raise Exception(f"Lỗi khi lấy danh sách fix requests: {str(e)}")
    
    def get_user_requests(
        self,
        current_user: User,
        status: Optional[str] = None
    ) -> List[FixRequestResponse]:
        """
        Lấy fix requests của user hiện tại
        """
        try:
            requests = self.fix_request_dao.get_by_user(current_user.username, status)
            return [self._convert_to_response(req) for req in requests]
        except Exception as e:
            logger.error(f"❌ Error getting user requests: {e}")
            raise Exception(f"Lỗi khi lấy danh sách fix requests: {str(e)}")
    
    def get_request_by_id(self, request_id: int) -> Optional[FixRequestResponse]:
        """
        Lấy chi tiết fix request
        """
        try:
            fix_request = self.fix_request_dao.get_by_id(request_id)
            if not fix_request:
                return None
            return self._convert_to_response(fix_request)
        except Exception as e:
            logger.error(f"❌ Error getting request detail: {e}")
            raise Exception(f"Lỗi khi lấy chi tiết fix request: {str(e)}")
    
    def delete_request(self, request_id: int, current_user: User) -> bool:
        """
        Xóa fix request (chỉ người tạo hoặc admin)
        """
        try:
            fix_request = self.fix_request_dao.get_by_id(request_id)
            
            if not fix_request:
                raise ValueError(f"Fix request ID {request_id} không tồn tại")
            
            # Kiểm tra quyền
            if current_user.role != 'admin' and fix_request.created_by != current_user.username:
                raise ValueError("Bạn không có quyền xóa fix request này")
            
            # Không cho xóa nếu đã được approve và đang thực thi
            if fix_request.status in ["executing", "completed"]:
                raise ValueError(f"Không thể xóa fix request đang {fix_request.status}")
            
            success = self.fix_request_dao.delete(fix_request)
            
            if success:
                logger.info(f"✅ Deleted fix request ID {request_id} by user {current_user.username}")
            
            return success
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"❌ Error deleting fix request: {e}")
            raise Exception(f"Lỗi khi xóa fix request: {str(e)}")
    
    def _convert_to_response(self, fix_request: FixRequest) -> FixRequestResponse:
        """Convert model to response DTO"""
        return FixRequestResponse(
            id=fix_request.id,
            rule_result_id=fix_request.rule_result_id,
            instance_id=fix_request.instance_id,
            title=fix_request.title,
            description=fix_request.description,
            status=fix_request.status,
            created_by=fix_request.created_by,
            created_at=fix_request.created_at,
            admin_id=fix_request.admin_id,
            approved_at=fix_request.approved_at,
            admin_comment=fix_request.admin_comment,
            executed_at=fix_request.executed_at,
            execution_result=fix_request.execution_result,
            error_message=fix_request.error_message
        )
# services/fix_action_log_service.py
import logging
import math
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from dao.fix_action_log_dao import FixActionLogDAO
from models.fix_action_log import FixActionLog
from schemas.fix_action_log import FixActionLogResponse, FixActionLogListResponse

class FixActionLogService:
    def __init__(self, db: Session):
        self.dao = FixActionLogDAO(db)

    def log_fix_action(
        self,
        user_id: int,
        username: str,
        rule_result_id: int,
        compliance_result_id: int,
        rule_name: Optional[str],
        old_status: str,
        new_status: str,
        command: Optional[str] = None,
        execution_output: Optional[str] = None,
        error_message: Optional[str] = None,
        is_success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> FixActionLogResponse:
        """
        Tạo log cho hành động fix rule result
        """
        try:
            # Tạo command mô tả nếu không có
            if not command:
                command = f"Update rule result {rule_result_id} status from '{old_status}' to '{new_status}'"
            
            # Tạo execution output mô tả nếu không có
            if not execution_output and is_success:
                execution_output = f"Successfully updated rule result status to '{new_status}'"

            log_entry = FixActionLog(
                user_id=user_id,
                username=username,
                rule_result_id=rule_result_id,
                compliance_result_id=compliance_result_id,
                rule_name=rule_name,
                old_status=old_status,
                new_status=new_status,
                command=command,
                execution_output=execution_output,
                error_message=error_message,
                is_success=is_success,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            created_log = self.dao.create(log_entry)
            
            # Log to file for debugging
            logging.info(f"Fix action logged: {username} updated rule {rule_result_id} from {old_status} to {new_status}")
            
            return self._convert_to_response(created_log)
            
        except Exception as e:
            logging.error(f"Error creating fix action log: {str(e)}")
            raise e

    def get_fix_logs_by_compliance(
        self,
        compliance_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> FixActionLogListResponse:
        """Lấy fix logs theo compliance ID"""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        skip = (page - 1) * page_size
        
        logs, total = self.dao.get_by_compliance_id(compliance_id, skip, page_size)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        log_responses = [self._convert_to_response(log) for log in logs]
        
        return FixActionLogListResponse(
            items=log_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def get_fix_logs_by_rule_result(
        self,
        rule_result_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> FixActionLogListResponse:
        """Lấy fix logs theo rule result ID"""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        skip = (page - 1) * page_size
        
        logs, total = self.dao.get_by_rule_result_id(rule_result_id, skip, page_size)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        log_responses = [self._convert_to_response(log) for log in logs]
        
        return FixActionLogListResponse(
            items=log_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def get_fix_logs_by_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> FixActionLogListResponse:
        """Lấy fix logs theo user ID"""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        skip = (page - 1) * page_size
        
        logs, total = self.dao.get_by_user_id(user_id, skip, page_size)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        log_responses = [self._convert_to_response(log) for log in logs]
        
        return FixActionLogListResponse(
            items=log_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def search_fix_logs(
        self,
        keyword: Optional[str] = None,
        user_id: Optional[int] = None,
        compliance_id: Optional[int] = None,
        rule_result_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        is_success: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> FixActionLogListResponse:
        """Tìm kiếm fix logs"""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        skip = (page - 1) * page_size
        
        logs, total = self.dao.search_fix_logs(
            keyword=keyword,
            user_id=user_id,
            compliance_id=compliance_id,
            rule_result_id=rule_result_id,
            old_status=old_status,
            new_status=new_status,
            is_success=is_success,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=page_size
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        log_responses = [self._convert_to_response(log) for log in logs]
        
        return FixActionLogListResponse(
            items=log_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def get_recent_fix_logs(
        self,
        hours: int = 24,
        page: int = 1,
        page_size: int = 20
    ) -> FixActionLogListResponse:
        """Lấy fix logs gần đây"""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        skip = (page - 1) * page_size
        
        logs, total = self.dao.get_recent_fix_logs(hours, skip, page_size)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        log_responses = [self._convert_to_response(log) for log in logs]
        
        return FixActionLogListResponse(
            items=log_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def get_failed_fix_logs(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> FixActionLogListResponse:
        """Lấy fix logs thất bại"""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        skip = (page - 1) * page_size
        
        logs, total = self.dao.get_failed_fix_logs(skip, page_size)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        log_responses = [self._convert_to_response(log) for log in logs]
        
        return FixActionLogListResponse(
            items=log_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def _convert_to_response(self, log: FixActionLog) -> FixActionLogResponse:
        """Convert model to response schema"""
        return FixActionLogResponse(
            id=log.id,
            user_id=log.user_id,
            username=log.username,
            rule_result_id=log.rule_result_id,
            compliance_result_id=log.compliance_result_id,
            rule_name=log.rule_name,
            old_status=log.old_status,
            new_status=log.new_status,
            command=log.command,
            execution_output=log.execution_output,
            error_message=log.error_message,
            is_success=log.is_success,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at
        )
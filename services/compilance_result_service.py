import asyncio
from datetime import datetime
import keyword
import logging
import math
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session


from dao.compliance_result_dao import ComplianceDAO


from dao.rule_dao import RuleDAO
from dao.rule_result_dao import RuleResultDAO
from dao.instance_dao import InstanceDAO
from dao.workload_dao import WorkLoadDAO
from models import workload
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
from schemas.compliance_result import (
    ComplianceResultCreate, ComplianceResultResponse,
     ComplianceResultListResponse,
    ComplianceSearchParams, RuleResultResponse
)
from services.sse_notification import notification_service

from services.rule_result_service import RuleResultService

from services.instance_service import InstanceService
from services.workload_service import WorkloadService


class ComplianceResultService:
    
    
    def __init__(self, db: Session):
        self.db = db
        self.dao = ComplianceDAO(db)
        self.rule_result_dao = RuleResultDAO(db)
        self.instance_dao = InstanceDAO(db)
        self.workload_dao = WorkLoadDAO(db)
        self.rule_dao = RuleDAO(db)

    

    def get_compliance_results(self, search_params: ComplianceSearchParams) -> ComplianceResultListResponse:
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.page_size))
        skip = (page - 1) * page_size
        
        results, total = self.dao.search_compliance_results(
            
            today=search_params.today,
            keyword=search_params.keyword,
            status=search_params.status,
            skip=skip,
            limit=page_size
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        result_responses = [self._convert_to_response(result) for result in results]
        
        return ComplianceResultListResponse(
            results=result_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def calculate_score(self, compliance_id: int):
        compliance_result = self.dao.get_by_id(compliance_id)
        if not compliance_result:
            return None

        pass_rule = self.rule_result_dao.count_passed_rules(compliance_id)

        total_rule = self.rule_result_dao.count_by_compliance_id(compliance_id)
        compliance_result.passed_rules = pass_rule
        compliance_result.total_rules = total_rule
        compliance_result.failed_rules = total_rule - pass_rule
        if total_rule > 0:
            compliance_result.score = (pass_rule / total_rule) * 100 
        else: 
            compliance_result.score = 0
        
        self.dao.update(compliance_result)
        

  

    def get_by_id(self, compliance_id: int) -> Optional[ComplianceResultResponse]:
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return None
            
            return  self._convert_to_response(compliance_result)
        except Exception as e:
            logging.error(f"Error getting compliance result detail {compliance_id}: {str(e)}")
            return None

   

   

  
    

    def create_pending_result(self, instance_id: int, workload_id : int) -> ComplianceResult:
        try:
            workload = self.workload_dao.get_by_id(workload_id)
            instance = self.instance_dao.get_by_id(instance_id)
            name = f"{instance.name} - {datetime.now()}"
            compliance_data = ComplianceResultCreate(
                instance_id=instance_id,
                name=name,
                status="pending",
                total_rules=0,
                passed_rules=0,
                failed_rules=0,
                score=0
            )
            
            compliance_dict = compliance_data.dict()
            compliance_model = ComplianceResult(**compliance_dict)
            return self.dao.create(compliance_model)
        except Exception as e:
            logging.error(f"Error creating pending result for instance {instance_id}: {str(e)}")
            raise e

   
    

    def update_status(self, compliance_id: int, status: str, detail_error: Optional[str] = None) -> bool:
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return False
                
            compliance_result.status = status
            compliance_result.detail_error = detail_error
            self.dao.update(compliance_result)
            if status == "failed":
                self._notify_completion_async(self._convert_to_response(compliance_result))
            return True
        except Exception as e:
            logging.error(f"Error updating compliance result status {compliance_id}: {str(e)}")
            return False

  

    def complete_result(self, compliance_id: int, rule_results: List[RuleResult], total_rules: int) -> bool:
        """Complete compliance result sau khi scan xong"""
        try:
            # Bulk create rule results
            if rule_results:
                self.rule_result_dao.create_bulk(rule_results)

            # Update compliance result
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return False

            rules_passed = sum(1 for rr in rule_results if rr.status == "passed")
            rules_failed = len(rule_results) - rules_passed

            compliance_result.status = "completed"
            compliance_result.total_rules = total_rules
            compliance_result.passed_rules = rules_passed
            compliance_result.failed_rules = rules_failed
            compliance_result.score = int((rules_passed / total_rules * 100) if total_rules > 0 else 0)
            
            self.dao.update(compliance_result)

            self._notify_completion_async(self._convert_to_response(compliance_result))

            return True
        except Exception as e:
            logging.error(f"Error completing compliance result {compliance_id}: {str(e)}")
            return False

    def _notify_completion_async(self, compliance_result_response: ComplianceResultResponse):
        """
        Gửi notification khi compliance scan hoàn thành
        
        ✅ CẬP NHẬT: Gửi notification cho USER SỞ HỮU instance đó, không broadcast
        """
        try:
            compliance_result_response.score = round(compliance_result_response.score, 2)
            
            # Lấy instance để biết user_id
            instance = self.instance_dao.get_by_id(compliance_result_response.instance_id)
            if not instance:
                logging.warning(f"⚠️ Instance {compliance_result_response.instance_id} not found, cannot notify")
                return
            
            # Lấy user_id từ instance
            user_id = instance.user_id
            if not user_id:
                logging.warning(f"⚠️ Instance {compliance_result_response.instance_id} has no owner, cannot notify")
                return
            
            message = {
                "type": compliance_result_response.status,
                "data": compliance_result_response.dict(),
                "timestamp": compliance_result_response.updated_at.isoformat()
            }
            
            # ✅ GỬI CHO USER CỤ THỂ (không broadcast)
            notification_service.notify_user(
                user_id=user_id,  # ✅ Gửi đúng cho owner của instance
                message=message
            )
            
            logging.info(f"✅ Notified user {user_id} about compliance scan {compliance_result_response.status} for instance {instance.name}")

        except Exception as e:
            logging.error(f"❌ Error sending completion notification: {str(e)}")
    def delete_compliance_result(self, compliance_id: int) -> bool:
        
        try:
            compliance = self.dao.get_by_id(compliance_id)
            if compliance:
                return self.dao.delete(compliance)
        except Exception as e:
            logging.error(f"Error deleting compliance result {compliance_id}: {str(e)}")
            return False

    

   

   
   

    def _convert_to_response(self, compliance: ComplianceResult) -> ComplianceResultResponse:
        
        instance = self.instance_dao.get_by_id(compliance.instance_id)
        workload = self.workload_dao.get_by_id(instance.workload_id) if instance else None
        return ComplianceResultResponse(
            id=compliance.id,
            instance_ip=instance.name if instance else None,
            name=compliance.name,
            instance_id=compliance.instance_id,
            status=compliance.status,
            total_rules=compliance.total_rules,
            passed_rules=compliance.passed_rules,
            failed_rules=compliance.failed_rules,
            score=compliance.score,
            scan_date=compliance.scan_date,
            
            updated_at=compliance.updated_at,
            workload_name=workload.name if workload else None,
          
            detail_error=compliance.detail_error
        )

  
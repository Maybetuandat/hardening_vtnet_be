import asyncio
import keyword
import logging
import math
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session


from dao.compliance_dao import ComplianceDAO


from models import workload
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
from schemas.compliance import (
    ComplianceResultCreate, ComplianceResultUpdate, ComplianceResultResponse,
     ComplianceResultListResponse,
    ComplianceSearchParams, RuleResultResponse
)
from services.notification_service import notification_service

from services.rule_result_service import RuleResultService
from services.server_service import ServerService
from services.workload_service import WorkloadService


class ComplianceResultService:
    
    
    def __init__(self, db: Session):
        self.db = db
        self.dao = ComplianceDAO(db)
        self.rule_result_service = RuleResultService(db)
        self.server_service = ServerService(db)
        self.workload_service = WorkloadService(db)

    

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

        pass_rule = self.rule_result_service.count_passed_rules(compliance_id)

        total_rule = self.rule_result_service.count_rules_by_compliance(compliance_id)
        compliance_result.passed_rules = pass_rule
        compliance_result.total_rules = total_rule
        compliance_result.failed_rules = total_rule - pass_rule
        if total_rule > 0:
            compliance_result.score = (pass_rule / total_rule) * 100 
        else: 
            compliance_result.score = 0
        self.dao.update(compliance_result)
        

  

    def get_compliance_result_detail(self, compliance_id: int) -> Optional[ComplianceResultResponse]:
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return None
            
            return  self._convert_to_response(compliance_result)
        except Exception as e:
            logging.error(f"Error getting compliance result detail {compliance_id}: {str(e)}")
            return None

   

   

  
    

    def create_pending_result(self, server_id: int) -> ComplianceResult:
        try:
            compliance_data = ComplianceResultCreate(
                server_id=server_id,
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
            logging.error(f"Error creating pending result for server {server_id}: {str(e)}")
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
                self.rule_result_service.create_bulk(rule_results)

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

    
    def _notify_completion_async(self, compliance_result_response : ComplianceResultResponse):
        


        try:
            compliance_result_response.score = round(compliance_result_response.score, 2)   
            message = {
                "type": compliance_result_response.status,
                "data": compliance_result_response.dict(),
                "timestamp": compliance_result_response.updated_at.isoformat()
            }
            notification_service.notify_compliance_completed_sync(message)

        except Exception as e:
            logging.error(f"Error sending completion notification: {str(e)}")
    def delete_compliance_result(self, compliance_id: int) -> bool:
        
        try:
            compliance = self.dao.get_by_id(compliance_id)
            if compliance:
                return self.dao.delete(compliance)
        except Exception as e:
            logging.error(f"Error deleting compliance result {compliance_id}: {str(e)}")
            return False

    

   

   
   

    def _convert_to_response(self, compliance: ComplianceResult) -> ComplianceResultResponse:
        
        server = self.server_service.get_server_by_id(compliance.server_id)
        workload = self.workload_service.get_workload_by_id(server.workload_id) if server else None
        return ComplianceResultResponse(
            id=compliance.id,
            server_ip=server.ip_address ,
            server_id=compliance.server_id,
            status=compliance.status,
            total_rules=compliance.total_rules,
            passed_rules=compliance.passed_rules,
            failed_rules=compliance.failed_rules,
            score=compliance.score,
            scan_date=compliance.scan_date,
            created_at=compliance.created_at,
            updated_at=compliance.updated_at,
            workload_name=workload.name if workload else None,
            server_hostname=server.hostname if server else None,
            detail_error=compliance.detail_error
        )

    def _convert_rule_result_to_response(self, rule_result: RuleResult) -> RuleResultResponse:
        return RuleResultResponse(
            id=rule_result.id,
            compliance_result_id=rule_result.compliance_result_id,
            rule_id=rule_result.rule_id,
            rule_name=rule_result.rule_name,
            status=rule_result.status,
            message=rule_result.message,
            details=rule_result.details,
            execution_time=rule_result.execution_time,
            created_at=rule_result.created_at,
            updated_at=rule_result.updated_at
        )
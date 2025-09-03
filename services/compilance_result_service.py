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
    ComplianceResultDetailResponse, ComplianceResultListResponse,
    ComplianceSearchParams, RuleResultResponse
)
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
        """Lấy danh sách compliance results với filter và pagination"""
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.page_size))
        skip = (page - 1) * page_size
        
        results, total = self.dao.search_compliance_results(
            server_id=search_params.server_id,
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
        

    def get_compliance_result_by_id(self, compliance_id: int) -> Optional[ComplianceResultResponse]:
        """Lấy compliance result theo ID"""
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return None
            return self._convert_to_response(compliance_result)
        except Exception as e:
            logging.error(f"Error getting compliance result {compliance_id}: {str(e)}")
            return None

    def get_compliance_result_detail(self, compliance_id: int) -> Optional[ComplianceResultDetailResponse]:
        """Lấy chi tiết compliance result bao gồm rule results"""
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return None
                
            # Get server info
            server = self.server_service.get_server_by_id(compliance_result.server_id)
            server_hostname = server.hostname if server else "Unknown"
            
            # Get workload info
            workload_name = None
            if server:
                workload = self.workload_service.dao.get_by_id(server.workload_id)
                workload_name = workload.name if workload else "Unknown"
                
            
            
            
            return ComplianceResultDetailResponse(
                id=compliance_result.id,
                server_id=compliance_result.server_id,
                status=compliance_result.status,
                total_rules=compliance_result.total_rules,
                passed_rules=compliance_result.passed_rules,
                failed_rules=compliance_result.failed_rules,
                score=compliance_result.score,
                scan_date=compliance_result.scan_date,
                created_at=compliance_result.created_at,
                updated_at=compliance_result.updated_at,
                server_ip = server.ip_address, 
                server_hostname=server_hostname,
                workload_name=workload_name
            )
        except Exception as e:
            logging.error(f"Error getting compliance result detail {compliance_id}: {str(e)}")
            return None

    def get_server_compliance_history(self, server_id: int, limit: int = 10) -> List[ComplianceResultResponse]:
        """Lấy lịch sử compliance của một server"""
        try:
            results, _ = self.dao.search_compliance_results(server_id=server_id, skip=0, limit=limit)
            return [self._convert_to_response(result) for result in results]
        except Exception as e:
            logging.error(f"Error getting server compliance history: {str(e)}")
            return []

    def get_compliance_status(self, compliance_id: int) -> Optional[Dict[str, Any]]:
        """Lấy trạng thái hiện tại của compliance scan"""
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return None
                
            server = self.server_service.get_server_by_id(compliance_result.server_id)
            server_hostname = server.hostname if server else "Unknown"
                
            return {
                "id": compliance_result.id,
                "server_id": compliance_result.server_id,
                "server_hostname": server_hostname,
                "status": compliance_result.status,
                "progress": {
                    "total_rules": compliance_result.total_rules,
                    "passed_rules": compliance_result.passed_rules,
                    "failed_rules": compliance_result.failed_rules,
                    "score": compliance_result.score
                },
                "scan_date": compliance_result.scan_date.isoformat(),
                "updated_at": compliance_result.updated_at.isoformat()
            }
        except Exception as e:
            logging.error(f"Error getting compliance status {compliance_id}: {str(e)}")
            return None

    def get_pending_result_by_server(self, server_id: int) -> Optional[ComplianceResult]:
        """Lấy compliance result đang pending của server"""
        try:
            return self.db.query(ComplianceResult).filter(
                ComplianceResult.server_id == server_id,
                ComplianceResult.status == "pending"
            ).first()
        except Exception as e:
            logging.error(f"Error getting pending result for server {server_id}: {str(e)}")
            return None

    

    def create_pending_result(self, server_id: int) -> ComplianceResult:
        """Tạo ComplianceResult với status pending cho server"""
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

    def create_compliance_result(self, compliance_data: ComplianceResultCreate) -> ComplianceResult:
        """Tạo ComplianceResult mới"""
        try:
            compliance_dict = compliance_data.dict()
            compliance_model = ComplianceResult(**compliance_dict)
            return self.dao.create(compliance_model)
        except Exception as e:
            logging.error(f"Error creating compliance result: {str(e)}")
            raise e

    

    def update_status(self, compliance_id: int, status: str, detail_error: Optional[str] = None) -> bool:
        """Update status của compliance result"""
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return False
                
            compliance_result.status = status
            compliance_result.detail_error = detail_error
            self.dao.update(compliance_result)
            return True
        except Exception as e:
            logging.error(f"Error updating compliance result status {compliance_id}: {str(e)}")
            return False

    def update_compliance_result(self, compliance_id: int, update_data: ComplianceResultUpdate) -> Optional[ComplianceResult]:
        """Update compliance result"""
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return None
            
            # Update các fields có trong update_data
            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                if hasattr(compliance_result, field) and value is not None:
                    setattr(compliance_result, field, value)
            
            return self.dao.update(compliance_result)
        except Exception as e:
            logging.error(f"Error updating compliance result {compliance_id}: {str(e)}")
            return None

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
            return True
        except Exception as e:
            logging.error(f"Error completing compliance result {compliance_id}: {str(e)}")
            return False

    

    def delete_compliance_result(self, compliance_id: int) -> bool:
        """Xóa compliance result"""
        try:
            return self.dao.delete(compliance_id)
        except Exception as e:
            logging.error(f"Error deleting compliance result {compliance_id}: {str(e)}")
            return False

    

    def cancel_compliance_scan(self, compliance_id: int) -> bool:
        """Hủy compliance scan đang chạy"""
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return False
                
            if compliance_result.status not in ["running", "pending"]:
                return False
                
            compliance_result.status = "cancelled"
            self.dao.update(compliance_result)
            return True
        except Exception as e:
            logging.error(f"Error cancelling compliance scan {compliance_id}: {str(e)}")
            return False

    def cancel_running_scan_by_server(self, server_id: int) -> bool:
        """Cancel scan đang chạy cho server"""
        try:
            running_result = self.db.query(ComplianceResult).filter(
                ComplianceResult.server_id == server_id,
                ComplianceResult.status.in_(["running", "pending"])
            ).first()
            
            if not running_result:
                return False
            
            running_result.status = "cancelled"
            self.dao.update(running_result)
            return True
        except Exception as e:
            logging.error(f"Error cancelling scan for server {server_id}: {str(e)}")
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
        )

    def _convert_rule_result_to_response(self, rule_result: RuleResult) -> RuleResultResponse:
        """Convert RuleResult model to response"""
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
# services/compliance_result_service.py
import logging
import math
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session


from dao.compliance_dao import ComplianceDAO
from dao.rule_result_dao import RuleResultDAO
from dao.server_dao import ServerDAO
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
from schemas.compliance import (
    ComplianceResultCreate, ComplianceResultUpdate, ComplianceResultResponse,
    ComplianceResultDetailResponse, ComplianceResultListResponse,
    ComplianceSearchParams, RuleResultResponse
)
from services.workload_service import WorkloadService


class ComplianceResultService:
    
    
    def __init__(self, db: Session):
        self.db = db
        self.dao = ComplianceDAO(db)
        self.rule_result_dao = RuleResultDAO(db)
        self.server_dao = ServerDAO(db)
        self.workload_service = WorkloadService(db)

    

    def get_compliance_results(self, search_params: ComplianceSearchParams) -> ComplianceResultListResponse:
        """Lấy danh sách compliance results với filter và pagination"""
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.page_size))
        skip = (page - 1) * page_size
        
        results, total = self.dao.search_compliance_results(
            server_id=search_params.server_id,
            workload_id=search_params.workload_id,
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
            server = self.server_dao.get_by_id(compliance_result.server_id)
            server_hostname = server.hostname if server else "Unknown"
            
            # Get workload info
            workload_name = None
            if server:
                workload = self.workload_service.dao.get_by_id(server.workload_id)
                workload_name = workload.name if workload else "Unknown"
                
            rule_results = self.rule_result_dao.get_by_compliance_id(compliance_id)
            rule_result_responses = [self._convert_rule_result_to_response(rr) for rr in rule_results]
            
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
                rule_results=rule_result_responses,
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
                
            server = self.server_dao.get_by_id(compliance_result.server_id)
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

    # ===== CREATE OPERATIONS =====

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

    # ===== UPDATE OPERATIONS =====

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
            return True
        except Exception as e:
            logging.error(f"Error completing compliance result {compliance_id}: {str(e)}")
            return False

    # ===== DELETE OPERATIONS =====

    def delete_compliance_result(self, compliance_id: int) -> bool:
        """Xóa compliance result"""
        try:
            return self.dao.delete(compliance_id)
        except Exception as e:
            logging.error(f"Error deleting compliance result {compliance_id}: {str(e)}")
            return False

    # ===== CANCEL OPERATIONS =====

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

    # ===== EXPORT OPERATIONS =====

    def export_compliance_report(self, compliance_id: int) -> Optional[Dict[str, Any]]:
        """Export báo cáo compliance"""
        try:
            compliance_detail = self.get_compliance_result_detail(compliance_id)
            if not compliance_detail:
                return None
                
            report = {
                "scan_info": {
                    "id": compliance_detail.id,
                    "server_id": compliance_detail.server_id,
                    "server_hostname": compliance_detail.server_hostname,
                    "workload_name": compliance_detail.workload_name,
                    "scan_date": compliance_detail.scan_date.isoformat(),
                    "status": compliance_detail.status,
                    "score": compliance_detail.score
                },
                "summary": {
                    "total_rules": compliance_detail.total_rules,
                    "passed_rules": compliance_detail.passed_rules,
                    "failed_rules": compliance_detail.failed_rules,
                    "success_rate": f"{(compliance_detail.passed_rules / compliance_detail.total_rules * 100):.1f}%" if compliance_detail.total_rules > 0 else "0%"
                },
                "detailed_results": [
                    {
                        "rule_id": rr.rule_id,
                        "rule_name": rr.rule_name,
                        "status": rr.status,
                        "message": rr.message,
                        "details": rr.details,
                        "execution_time": rr.execution_time
                    } for rr in compliance_detail.rule_results
                ]
            }
            
            return report
            
        except Exception as e:
            logging.error(f"Error exporting compliance report {compliance_id}: {str(e)}")
            return None

    # ===== STATISTICS OPERATIONS =====

    def get_compliance_summary_by_workload(self, workload_id: Optional[int] = None) -> Dict[str, Any]:
        """Lấy tổng quan compliance theo workload"""
        try:
            # Get compliance results (optionally filtered by workload)
            if workload_id:
                # Get servers of workload first
                servers, _ = self.server_dao.search_servers(workload_id=workload_id, status=True, skip=0, limit=10000)
                server_ids = [s.id for s in servers]
                
                if not server_ids:
                    return {
                        "workload_id": workload_id,
                        "total_servers": 0,
                        "scanned_servers": 0,
                        "average_score": 0,
                        "status_breakdown": {}
                    }
                
                # Get compliance results for these servers
                all_results = []
                for server_id in server_ids:
                    results, _ = self.dao.search_compliance_results(server_id=server_id, skip=0, limit=100)
                    all_results.extend(results)
            else:
                all_results, _ = self.dao.get_all(skip=0, limit=10000)
            
            status_counts = {
                "pending": 0,
                "running": 0, 
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            
            total_score = 0
            completed_count = 0
            
            for result in all_results:
                if result.status in status_counts:
                    status_counts[result.status] += 1
                    
                if result.status == "completed":
                    total_score += result.score
                    completed_count += 1
            
            avg_score = int(total_score / completed_count) if completed_count > 0 else 0
            
            return {
                "workload_id": workload_id,
                "total_scans": len(all_results),
                "status_breakdown": status_counts,
                "average_compliance_score": avg_score,
                "last_scan_date": max([r.scan_date for r in all_results]).isoformat() if all_results else None
            }
            
        except Exception as e:
            logging.error(f"Error getting compliance summary: {str(e)}")
            return {
                "workload_id": workload_id,
                "total_scans": 0,
                "status_breakdown": {},
                "average_compliance_score": 0,
                "last_scan_date": None
            }

    def get_compliance_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê tổng quan compliance"""
        try:
            all_results, total = self.dao.get_all(skip=0, limit=10000)
            
            status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}
            total_score = 0
            completed_count = 0
            
            for result in all_results:
                if result.status in status_counts:
                    status_counts[result.status] += 1
                    
                if result.status == "completed":
                    total_score += result.score
                    completed_count += 1
            
            avg_score = int(total_score / completed_count) if completed_count > 0 else 0
            
            return {
                "total_scans": total,
                "status_breakdown": status_counts,
                "average_compliance_score": avg_score,
                "last_scan_date": max([r.scan_date for r in all_results]).isoformat() if all_results else None
            }
        except Exception as e:
            logging.error(f"Error getting compliance statistics: {str(e)}")
            return {
                "total_scans": 0,
                "status_breakdown": {},
                "average_compliance_score": 0,
                "last_scan_date": None
            }

    def get_rule_results_by_status(self, compliance_id: int, status: Optional[str] = None) -> Dict[str, Any]:
        """Lấy rule results theo status"""
        try:
            compliance_detail = self.get_compliance_result_detail(compliance_id)
            if not compliance_detail:
                return {"error": "Compliance result not found"}
            
            rule_results = compliance_detail.rule_results
            
            if status:
                rule_results = [rr for rr in rule_results if rr.status == status]
            
            return {
                "compliance_id": compliance_id,
                "filter_status": status,
                "total_results": len(rule_results),
                "rule_results": rule_results
            }
        except Exception as e:
            logging.error(f"Error getting rule results by status: {str(e)}")
            return {"error": str(e)}

    # ===== PRIVATE HELPER METHODS =====

    def _convert_to_response(self, compliance: ComplianceResult) -> ComplianceResultResponse:
        """Convert ComplianceResult model to response"""
        return ComplianceResultResponse(
            id=compliance.id,
            server_id=compliance.server_id,
            status=compliance.status,
            total_rules=compliance.total_rules,
            passed_rules=compliance.passed_rules,
            failed_rules=compliance.failed_rules,
            score=compliance.score,
            scan_date=compliance.scan_date,
            created_at=compliance.created_at,
            updated_at=compliance.updated_at
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
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any, Optional
from models.server import Server
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
import logging


class DashboardDAO:
    def __init__(self, db: Session):
        self.db = db
    
    def get_total_active_servers(self) -> int:
        try:
            return self.db.query(Server).filter(Server.status == True).count()
        except Exception as e:
            logging.error(f"Error getting total active servers: {str(e)}")
            return 0
    
    def get_compliance_statistics(self) -> Dict[str, Any]:
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

            # Query cho completed results để tính compliance rate
            completed_stats_query = self.db.query(
                func.sum(ComplianceResult.score).label('total_score'),
                func.count(ComplianceResult.id).label('total_count')
            ).filter(
                ComplianceResult.status == 'completed', 
                ComplianceResult.scan_date >= today_start,
                ComplianceResult.scan_date <= today_end
            )
            
            completed_result = completed_stats_query.first()
            
            # Query để tính tổng failed_rules từ tất cả ComplianceResult
            failed_rules_query = self.db.query(
                func.sum(ComplianceResult.failed_rules).label('total_failed_rules')
            ).filter(
                ComplianceResult.scan_date >= today_start,
                ComplianceResult.scan_date <= today_end
            )
            
            failed_rules_result = failed_rules_query.first()
            
            # Query để đếm số ComplianceResult có status = 'failed'
            failed_compliance_query = self.db.query(
                func.count(ComplianceResult.id).label('failed_compliance_count')
            ).filter(
                ComplianceResult.status == 'failed',
                ComplianceResult.scan_date >= today_start,
                ComplianceResult.scan_date <= today_end
            )
            
            failed_compliance_result = failed_compliance_query.first()
            
            # Tính compliance_rate từ completed results
            compliance_rate = 0.0
            if completed_result and completed_result.total_count > 0 and completed_result.total_score is not None:
                compliance_rate = round(float(completed_result.total_score) / float(completed_result.total_count), 1)
            
            # Tính critical_issues = số failed_rules + số ComplianceResult failed
            total_failed_rules = int(failed_rules_result.total_failed_rules or 0) if failed_rules_result else 0
            failed_compliance_count = int(failed_compliance_result.failed_compliance_count or 0) if failed_compliance_result else 0
            critical_issues = total_failed_rules + failed_compliance_count
            
            return {
                "compliance_rate": compliance_rate,
                "critical_issues": critical_issues
            }
            
        except Exception as e:
            logging.error(f"Error getting compliance statistics: {str(e)}")
            return {
                "compliance_rate": 0.0,
                "critical_issues": 0
            }
    
    def get_last_audit_time(self) -> Optional[str]:
        try:
            latest_result = self.db.query(ComplianceResult)\
                .filter(ComplianceResult.status == 'completed')\
                .order_by(desc(ComplianceResult.created_at))\
                .first()
            
            if latest_result:
                return latest_result.created_at.strftime("%Y-%m-%d %H:%M:%S")
            return None
            
        except Exception as e:
            logging.error(f"Error getting last audit time: {str(e)}")
            return None
    
    def get_dashboard_statistics(self) -> Dict[str, Any]:
        try:
            total_nodes = self.get_total_active_servers()
            compliance_stats = self.get_compliance_statistics()
            last_audit = self.get_last_audit_time()
            
            return {
                "total_nodes": total_nodes,
                "compliance_rate": compliance_stats["compliance_rate"],
                "critical_issues": compliance_stats["critical_issues"],
                "last_audit": last_audit
            }
            
        except Exception as e:
            logging.error(f"Error getting dashboard statistics: {str(e)}")
            return {
                "total_nodes": 0,
                "compliance_rate": 0.0,
                "critical_issues": 0,
                "last_audit": None
            }
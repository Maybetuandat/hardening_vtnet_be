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

            stats_query = self.db.query(
                func.sum(ComplianceResult.score).label('total_score'),
                func.count(ComplianceResult.id).label('total_count'),
                func.sum(ComplianceResult.failed_rules).label('total_critical_issues')

            ).filter(ComplianceResult.status == 'completed', 
                     ComplianceResult.scan_date >= today_start,
                    ComplianceResult.scan_date <= today_end)
            
            result = stats_query.first()
            
            
            if not result or result.total_count == 0 or result.total_score is None:
                return {
                    "compliance_rate": 0.0,
                    "critical_issues": 0
                }
            
            
            compliance_rate = round(float(result.total_score) / float(result.total_count), 1)
            critical_issues = int(result.total_critical_issues or 0)
            
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
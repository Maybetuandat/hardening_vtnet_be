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

            
            subquery = (
                self.db.query(
                    ComplianceResult.id,
                    ComplianceResult.status,
                    func.row_number()
                    .over(
                        partition_by=Server.ip_address,
                        order_by=desc(ComplianceResult.scan_date)
                    )
                    .label("rn")
                )
                .join(ComplianceResult.server)
                .filter(
                    ComplianceResult.scan_date >= today_start,
                    ComplianceResult.scan_date <= today_end
                )
                .subquery()
            )

            
            latest_query = (
                self.db.query(subquery.c.status)
                .filter(subquery.c.rn == 1)
            )

            latest_results = [row.status for row in latest_query.all()]

            total = len(latest_results)
            completed_count = sum(1 for s in latest_results if s == "completed")
            failed_count = total - completed_count 

            print("Debug - completed count:", completed_count)
            print("Debug - total count:", total)
            compliance_rate = round(completed_count / total, 2) if total > 0 else 0.0
            critical_issues = failed_count

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
                .order_by(desc(ComplianceResult.scan_date))\
                .first()
            
            if latest_result:
                return latest_result.scan_date.strftime("%Y-%m-%d %H:%M:%S")
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
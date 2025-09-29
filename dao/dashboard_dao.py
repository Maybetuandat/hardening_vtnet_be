from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any, Optional
from models.instance import Instance
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
import logging


class DashboardDAO:
    def __init__(self, db: Session):
        self.db = db

    def get_total_active_instances(self, current_user_id: Optional[int]) -> int:
        try:
            query = self.db.query(Instance).filter(Instance.status == True)
            if current_user_id:
                query = query.filter(Instance.user_id == current_user_id)
            return query.count()
        except Exception as e:
            logging.error(f"Error getting total active instances: {str(e)}")
            return 0

    def get_compliance_statistics(self, current_user_id: Optional[int]) -> Dict[str, Any]:
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

            
            subquery = (
                self.db.query(
                    ComplianceResult.id,
                    ComplianceResult.status,
                    func.row_number()
                    .over(
                        partition_by=Instance.name,
                        order_by=desc(ComplianceResult.scan_date)
                    )
                    .label("rn")
                )
                .join(ComplianceResult.instance)
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
    
    def get_dashboard_statistics(self, current_user_id: Optional[int]) -> Dict[str, Any]:
        try:
            
            total_nodes = self.get_total_active_instances(current_user_id)
            compliance_stats = self.get_compliance_statistics(current_user_id)
            last_audit = self.get_last_audit_time(current_user_id)
            
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
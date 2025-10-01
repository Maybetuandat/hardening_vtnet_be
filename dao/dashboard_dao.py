# dao/dashboard_dao.py - CẬP NHẬT
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import Dict, Any, Optional, List
from models.instance import Instance
from models.compliance_result import ComplianceResult
from models.workload import WorkLoad
from models.user import User
import logging

logger = logging.getLogger(__name__)

class DashboardDAO:
    def __init__(self, db: Session):
        self.db = db

    def get_workload_statistics(self, current_user: User) -> List[Dict[str, Any]]:
        """
        Lấy thống kê instances theo workload
        - pass_count: số instance có status = 1 (active)
        - fail_count: số instance có status = 0 (inactive)
        """
        try:
            logger.info(f"🔍 Getting workload stats for user: {current_user.username} (role: {current_user.role})")
            
            query = (
                self.db.query(
                    WorkLoad.name.label("workload_name"),
                    func.count(Instance.id).label("total"),
                    func.sum(
                        case(
                            (Instance.status == True, 1),
                            else_=0
                        )
                    ).label("pass_count"),
                    func.sum(
                        case(
                            (Instance.status == False, 1),
                            else_=0
                        )
                    ).label("fail_count")
                )
                .join(Instance, Instance.workload_id == WorkLoad.id)
            )

            # Filter theo user nếu không phải admin
            if current_user.role != "admin":
                query = query.filter(Instance.user_id == current_user.id)
                logger.info(f"👤 Filtering by user_id: {current_user.id}")
            else:
                logger.info("👑 Admin user - getting all workloads")

            query = query.group_by(WorkLoad.name).order_by(desc("total"))

            results = query.all()
            
            logger.info(f"📊 Found {len(results)} workload groups")

            workload_stats = []
            for row in results:
                workload_stat = {
                    "workload_name": row.workload_name,
                    "pass_count": int(row.pass_count or 0),
                    "fail_count": int(row.fail_count or 0),
                    "total": int(row.total or 0)
                }
                workload_stats.append(workload_stat)
                logger.info(f"  📌 {row.workload_name}: pass={workload_stat['pass_count']}, fail={workload_stat['fail_count']}")

            if not workload_stats:
                logger.warning("⚠️ No workload stats found")
                
                # Debug info
                instance_count = self.db.query(Instance)
                if current_user.role != "admin":
                    instance_count = instance_count.filter(Instance.user_id == current_user.id)
                instance_count = instance_count.count()
                logger.warning(f"  Total instances: {instance_count}")
                
                instances_with_workload = self.db.query(Instance).filter(
                    Instance.workload_id.isnot(None)
                )
                if current_user.role != "admin":
                    instances_with_workload = instances_with_workload.filter(
                        Instance.user_id == current_user.id
                    )
                instances_with_workload_count = instances_with_workload.count()
                logger.warning(f"  Instances with workload: {instances_with_workload_count}")

            return workload_stats

        except Exception as e:
            logger.error(f"❌ Error getting workload statistics: {str(e)}", exc_info=True)
            return []

    def get_total_active_instances(self, current_user: User) -> int:
        """Lấy tổng số instance (bao gồm cả active và inactive)"""
        try:
            query = self.db.query(Instance)
            
            if current_user.role != "admin":
                query = query.filter(Instance.user_id == current_user.id)
            
            count = query.count()
            logger.info(f"📊 Total instances: {count}")
            return count
        except Exception as e:
            logger.error(f"❌ Error getting total instances: {str(e)}")
            return 0

    def get_instance_statistics(self, current_user: User) -> Dict[str, Any]:
        """
        Lấy thống kê tổng quan về instances
        - passed_servers: số instance active (status = True)
        - failed_servers: số instance inactive (status = False)
        """
        try:
            logger.info(f"🔍 Getting instance stats for user: {current_user.username}")
            
            query = self.db.query(Instance)
            
            if current_user.role != "admin":
                query = query.filter(Instance.user_id == current_user.id)
            
            total = query.count()
            active_count = query.filter(Instance.status == True).count()
            inactive_count = query.filter(Instance.status == False).count()
            
            compliance_rate = round((active_count / total * 100), 2) if total > 0 else 0.0
            
            logger.info(f"  ✅ Active: {active_count}, ❌ Inactive: {inactive_count}, 📊 Rate: {compliance_rate}%")

            return {
                "compliance_rate": compliance_rate,
                "critical_issues": inactive_count,
                "passed_servers": active_count,
                "failed_servers": inactive_count
            }

        except Exception as e:
            logger.error(f"❌ Error getting instance statistics: {str(e)}", exc_info=True)
            return {
                "compliance_rate": 0.0,
                "critical_issues": 0,
                "passed_servers": 0,
                "failed_servers": 0
            }

    def get_last_audit_time(self, current_user: User) -> Optional[str]:
        """Lấy thời gian scan gần nhất"""
        try:
            query = self.db.query(ComplianceResult).join(ComplianceResult.instance)
            
            if current_user.role != "admin":
                query = query.filter(Instance.user_id == current_user.id)
            
            latest_result = query.order_by(desc(ComplianceResult.scan_date)).first()
            
            if latest_result:
                return latest_result.scan_date.strftime("%Y-%m-%d %H:%M:%S")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting last audit time: {str(e)}")
            return None
    
    def get_dashboard_statistics(self, current_user: User) -> Dict[str, Any]:
        """
        Lấy tất cả thống kê dashboard
        Dựa trên INSTANCE STATUS (không phải compliance result)
        """
        try:
            logger.info(f"🎯 Getting dashboard statistics for {current_user.username}")
            
            total_nodes = self.get_total_active_instances(current_user)
            instance_stats = self.get_instance_statistics(current_user)
            last_audit = self.get_last_audit_time(current_user)
            workload_stats = self.get_workload_statistics(current_user)
            
            result = {
                "total_nodes": total_nodes,
                "compliance_rate": instance_stats["compliance_rate"],
                "critical_issues": instance_stats["critical_issues"],
                "last_audit": last_audit,
                "passed_servers": instance_stats["passed_servers"],
                "failed_servers": instance_stats["failed_servers"],
                "workload_stats": workload_stats
            }
            
            logger.info(f"✅ Dashboard stats compiled successfully")
            logger.info(f"   Total: {total_nodes}, Active: {instance_stats['passed_servers']}, Inactive: {instance_stats['failed_servers']}")
            logger.info(f"   Workload groups: {len(workload_stats)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting dashboard statistics: {str(e)}", exc_info=True)
            return {
                "total_nodes": 0,
                "compliance_rate": 0.0,
                "critical_issues": 0,
                "last_audit": None,
                "passed_servers": 0,
                "failed_servers": 0,
                "workload_stats": []
            }
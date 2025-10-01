from sqlalchemy.orm import Session
from dao.dashboard_dao import DashboardDAO
from schemas.dashboard import DashboardStatsResponse, WorkloadStats
from models.user import User
from typing import Dict, Any, Optional
import logging


class DashboardService:
    def __init__(self, db: Session):
        self.dao = DashboardDAO(db)
        self.db = db

    def get_dashboard_statistics(self, current_user: User) -> DashboardStatsResponse:
        """
        Lấy thống kê dashboard
        - Admin: lấy tất cả dữ liệu trong hệ thống
        - User: chỉ lấy dữ liệu của instance thuộc về họ
        
        Bao gồm:
        - Total nodes (server đang hoạt động)
        - Compliance rate (tỷ lệ tuân thủ trung bình)
        - Critical issues (số lỗi critical)
        - Last audit (thời gian scan gần nhất)
        - Passed/Failed servers (cho biểu đồ tròn)
        - Workload statistics (cho biểu đồ cột ngang)
        """
        try:
            # Truyền current_user vào DAO thay vì current_user.id
            stats = self.dao.get_dashboard_statistics(current_user)
            
            # Convert workload stats to WorkloadStats objects
            workload_stats_list = [
                WorkloadStats(
                    workload_name=ws["workload_name"],
                    pass_count=ws["pass_count"],
                    fail_count=ws["fail_count"],
                    total=ws["total"]
                )
                for ws in stats.get("workload_stats", [])
            ]
            
            return DashboardStatsResponse(
                total_nodes=stats["total_nodes"],
                compliance_rate=stats["compliance_rate"],
                critical_issues=stats["critical_issues"],
                last_audit=stats["last_audit"],
                passed_servers=stats["passed_servers"],
                failed_servers=stats["failed_servers"],
                workload_stats=workload_stats_list
            )
            
        except Exception as e:
            logging.error(f"Error in dashboard service: {str(e)}")
            # Trả về giá trị mặc định khi có lỗi
            return DashboardStatsResponse(
                total_nodes=0,
                compliance_rate=0.0,
                critical_issues=0,
                last_audit=None,
                passed_servers=0,
                failed_servers=0,
                workload_stats=[]
            )
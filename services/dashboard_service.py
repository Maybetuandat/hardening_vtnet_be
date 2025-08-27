from sqlalchemy.orm import Session
from dao.dashboard_dao import DashboardDAO
from schemas.dashboard import DashboardStatsResponse
from typing import Dict, Any
import logging


class DashboardService:
    def __init__(self, db: Session):
        self.dao = DashboardDAO(db)
        self.db = db
    
    def get_dashboard_statistics(self) -> DashboardStatsResponse:
        """
        Lấy thống kê dashboard bao gồm:
        - Total nodes (server đang hoạt động)
        - Compliance rate (tỷ lệ tuân thủ trung bình)
        - Critical issues (số lỗi critical)
        - Last audit (thời gian scan gần nhất)
        """
        try:
            stats = self.dao.get_dashboard_statistics()
            
            return DashboardStatsResponse(
                total_nodes=stats["total_nodes"],
                compliance_rate=stats["compliance_rate"],
                critical_issues=stats["critical_issues"],
                last_audit=stats["last_audit"]
            )
            
        except Exception as e:
            logging.error(f"Error in dashboard service: {str(e)}")
            # Trả về giá trị mặc định khi có lỗi
            return DashboardStatsResponse(
                total_nodes=0,
                compliance_rate=0.0,
                critical_issues=0,
                last_audit=None
            )
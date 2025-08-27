from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config.config_database import get_db
from schemas.dashboard import DashboardStatsResponse
from services.dashboard_service import DashboardService


router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("/statistics", response_model=DashboardStatsResponse)
def get_dashboard_statistics(
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Lấy thống kê cho dashboard:
    - Total nodes: số lượng server đang hoạt động
    - Compliance rate: tỷ lệ tuân thủ trung bình
    - Critical issues: tổng số lỗi critical
    - Last audit: thời gian scan gần nhất
    """
    try:
        return dashboard_service.get_dashboard_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thống kê dashboard: {str(e)}")
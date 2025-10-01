from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config.config_database import get_db
from schemas.dashboard import DashboardStatsResponse
from services.dashboard_service import DashboardService
from utils.auth import require_user


router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("/statistics", response_model=DashboardStatsResponse)
def get_dashboard_statistics(
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    current_user = Depends(require_user())
):
    """
    Lấy thống kê cho dashboard:
    - Admin: Lấy tất cả thống kê của toàn bộ hệ thống
    - User: Chỉ lấy thống kê của các instance thuộc về user đó
    
    Bao gồm:
    - Total nodes: số lượng server đang hoạt động
    - Compliance rate: tỷ lệ tuân thủ trung bình
    - Critical issues: tổng số lỗi critical
    - Last audit: thời gian scan gần nhất
    - Passed servers: số lượng server đạt chuẩn
    - Failed servers: số lượng server không đạt chuẩn
    - Workload stats: thống kê theo từng workload
    """
    try:
        # Truyền current_user object thay vì current_user.id
        return dashboard_service.get_dashboard_statistics(current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thống kê dashboard: {str(e)}")
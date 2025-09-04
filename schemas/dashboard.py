from pydantic import BaseModel, Field
from typing import Optional


class DashboardStatsResponse(BaseModel):
    """Response schema cho dashboard statistics"""
    total_nodes: int = Field(..., description="Tổng số server đang hoạt động")
    compliance_rate: float = Field(..., description="Tỷ lệ tuân thủ trung bình (%)", ge=0, le=100)
    critical_issues: int = Field(..., description="Tổng số lỗi critical", ge=0)
    last_audit: Optional[str] = Field(None, description="Thời gian audit gần nhất (YYYY-MM-DD HH:MM:SS)")
    
    class Config:
        from_attributes = True
       
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
        json_schema_extra = {
            "example": {
                "total_nodes": 247,
                "compliance_rate": 78.5,
                "critical_issues": 12,
                "last_audit": "2024-01-30 14:32:00"
            }
        }
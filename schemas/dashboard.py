from pydantic import BaseModel, Field
from typing import Optional


class DashboardStatsResponse(BaseModel):
    """Response schema for dashboard statistics"""
    total_nodes: int = Field(..., description="Total number of active servers")
    compliance_rate: float = Field(..., description="Average compliance rate (%)", ge=0, le=100)
    critical_issues: int = Field(..., description="Total number of critical issues", ge=0)
    last_audit: Optional[str] = Field(None, description="Last audit time (YYYY-MM-DD HH:MM:SS)")
    
    class Config:
        from_attributes = True
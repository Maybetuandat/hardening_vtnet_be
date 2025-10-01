from pydantic import BaseModel, Field
from typing import Optional, List


class WorkloadStats(BaseModel):
    """Statistics for each workload"""
    workload_name: str = Field(..., description="Name of the workload")
    pass_count: int = Field(..., description="Number of passed servers in this workload")
    fail_count: int = Field(..., description="Number of failed servers in this workload")
    total: int = Field(..., description="Total servers in this workload")
    
    class Config:
        from_attributes = True


class DashboardStatsResponse(BaseModel):
    """Response schema for dashboard statistics"""
    total_nodes: int = Field(..., description="Total number of active servers")
    compliance_rate: float = Field(..., description="Average compliance rate (%)", ge=0, le=100)
    critical_issues: int = Field(..., description="Total number of critical issues", ge=0)
    last_audit: Optional[str] = Field(None, description="Last audit time (YYYY-MM-DD HH:MM:SS)")
    
    # Thêm dữ liệu cho biểu đồ
    passed_servers: int = Field(..., description="Number of passed servers")
    failed_servers: int = Field(..., description="Number of failed servers")
    workload_stats: List[WorkloadStats] = Field(default=[], description="Statistics by workload")
    
    class Config:
        from_attributes = True
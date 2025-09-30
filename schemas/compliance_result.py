from datetime import datetime
from decimal import Decimal
from http import server
from typing import List, Optional
from pydantic import BaseModel, Field, validator

from schemas.rule_result import RuleResultResponse


class ComplianceResultBase(BaseModel):
    instance_id: int = Field(..., description="ID of the instance being scanned")
    name: Optional[str] = Field(None, description="Name of the scan")
    status: str = Field(..., description="Scan status: pending, running, completed, failed")
    total_rules: int = Field(0, description="Total number of workload rules")
    passed_rules: int = Field(0, description="Number of passed rules")
    failed_rules: int = Field(0, description="Number of failed rules")
    score: float = Field(0, ge=0, le=100, description="Compliance score (0-100)")
    detail_error: Optional[str] = Field(None, description="Error details if any")

    @validator('score', pre=True)
    def convert_decimal_to_float(cls, v):
        if isinstance(v, Decimal):
            return float(v)
        return v


class ComplianceResultCreate(ComplianceResultBase):
    pass


class ComplianceResultResponse(ComplianceResultBase):
    id: int
  
    scan_date: datetime
    updated_at: datetime
    instance_ip: Optional[str] = Field(None, description="IP address of the scanned instance")
    workload_name: Optional[str] = Field(None, description="Workload name")
   
    
    class Config:
        from_attributes = True


class ComplianceResultListResponse(BaseModel):
    results: List[ComplianceResultResponse] = Field(..., description="List of compliance results")
    total: int = Field(..., description="Total number of results")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        from_attributes = True


class ComplianceScanRequest(BaseModel):
    server_ids: Optional[List[int]] = Field(None, description="List of specific server IDs to scan (None = scan all servers)")
    batch_size: int = Field(10, ge=1, le=50, description="Number of servers per batch")


class ComplianceScanResponse(BaseModel):
    message: str = Field(..., description="Result message")
    total_instances: int = Field(..., description="Total number of servers to scan")
    started_scans: List[int] = Field(..., description="List of created compliance_result IDs")


class ComplianceSearchParams(BaseModel):
    today: Optional[str] = Field(None, description="Filter results for today")
    list_workload_id: Optional[List[int]] = Field(None, description="Workload IDs")
    keyword: Optional[str] = Field(None, description="Search keyword by server IP")
    status: Optional[str] = Field(None, description="Filter by status")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page")
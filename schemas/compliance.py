from datetime import datetime
from decimal import Decimal
from http import server
from typing import List, Optional
from pydantic import BaseModel, Field, validator

from schemas.rule_result import RuleResultResponse


class ComplianceResultBase(BaseModel):
    server_id: int = Field(..., description="ID của server được scan")
    status: str = Field(..., description="Trạng thái scan: pending, running, completed, failed")
    total_rules: int = Field(0, description="Tổng số rules của workload")
    passed_rules: int = Field(0, description="Số rules passed")
    failed_rules: int = Field(0, description="Số rules failed")
    score: float = Field(0, ge=0, le=100, description="Điểm compliance (0-100)")
   

    @validator('score', pre=True)
    def convert_decimal_to_float(cls, v):
        
        if isinstance(v, Decimal):
            return float(v)
        return v


class ComplianceResultCreate(ComplianceResultBase):
    pass


class ComplianceResultUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Trạng thái scan")
    total_rules: Optional[int] = Field(None, description="Tổng số rules")
    passed_rules: Optional[int] = Field(None, description="Số rules passed")
    failed_rules: Optional[int] = Field(None, description="Số rules failed")
    score: Optional[float] = Field(None, ge=0, le=100, description="Điểm compliance")

    @validator('score', pre=True)
    def convert_decimal_to_float(cls, v):
        
        if v is not None and isinstance(v, Decimal):
            return float(v)
        return v

class ComplianceResultResponse(ComplianceResultBase):
    id: int
    server_ip: Optional[str] = Field(None, description="IP của server được scan")
    scan_date: datetime
    created_at: datetime
    updated_at: datetime
    server_ip: Optional[str] = Field(None, description="IP của server được scan")
    class Config:
        from_attributes = True


class ComplianceResultDetailResponse(ComplianceResultResponse):
    
    server_hostname: Optional[str] = Field(None, description="Hostname của server")
    workload_name: Optional[str] = Field(None, description="Tên workload")


class ComplianceResultListResponse(BaseModel):
    results: List[ComplianceResultResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class ComplianceScanRequest(BaseModel):
    server_ids: Optional[List[int]] = Field(None, description="Danh sách server IDs cụ thể cần scan (None = scan all servers)")
    batch_size: int = Field(100, ge=1, le=500, description="Số server mỗi batch")

 


class ComplianceScanResponse(BaseModel):
    message: str = Field(..., description="Thông báo kết quả")
    total_servers: int = Field(..., description="Tổng số servers sẽ scan")
    started_scans: List[int] = Field(..., description="Danh sách compliance_result IDs được tạo")


class ComplianceSearchParams(BaseModel):
    server_id: Optional[int] = Field(None, description="ID của server")
    keyword: Optional[str] = Field(None, description="Từ khóa tìm kiếm theo ip server")
    status: Optional[str] = Field(None, description="Filter theo trạng thái")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    
# schemas/compliance.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ComplianceResultBase(BaseModel):
    server_id: int = Field(..., description="ID của server được scan")
    status: str = Field(..., description="Trạng thái scan: pending, running, completed, failed")
    total_rules: int = Field(0, description="Tổng số rules của workload")
    passed_rules: int = Field(0, description="Số rules passed")
    failed_rules: int = Field(0, description="Số rules failed")
    score: int = Field(0, ge=0, le=100, description="Điểm compliance (0-100)")


class ComplianceResultCreate(ComplianceResultBase):
    pass


class ComplianceResultUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Trạng thái scan")
    total_rules: Optional[int] = Field(None, description="Tổng số rules")
    passed_rules: Optional[int] = Field(None, description="Số rules passed")
    failed_rules: Optional[int] = Field(None, description="Số rules failed")
    score: Optional[int] = Field(None, ge=0, le=100, description="Điểm compliance")


class ComplianceResultResponse(ComplianceResultBase):
    id: int
    scan_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RuleResultBase(BaseModel):
    rule_id: int = Field(..., description="ID của rule")
    rule_name: Optional[str] = Field(None, description="Tên rule")
    status: str = Field(..., description="Trạng thái rule: passed, failed, skipped, error")
    message: Optional[str] = Field(None, description="Thông báo kết quả")
    details: Optional[str] = Field(None, description="Chi tiết kết quả (JSON string)")
    execution_time: Optional[int] = Field(None, description="Thời gian thực thi (seconds)")


class RuleResultCreate(RuleResultBase):
    compliance_result_id: int = Field(..., description="ID của compliance result")


class RuleResultUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Trạng thái rule")
    message: Optional[str] = Field(None, description="Thông báo kết quả")
    details: Optional[str] = Field(None, description="Chi tiết kết quả")
    execution_time: Optional[int] = Field(None, description="Thời gian thực thi")


class RuleResultResponse(RuleResultBase):
    id: int
    compliance_result_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceResultDetailResponse(ComplianceResultResponse):
    rule_results: List[RuleResultResponse] = Field([], description="Danh sách kết quả từng rule")
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

    @validator('server_ids')
    def validate_server_ids(cls, v):
        if v is not None:
            if len(v) == 0:
                raise ValueError("Danh sách server_ids không được rỗng")
            if len(v) > 10000:
                raise ValueError("Số lượng server tối đa là 10,000")
            # Remove duplicates và sort
            return sorted(list(set(v)))
        return v


class ComplianceScanResponse(BaseModel):
    message: str = Field(..., description="Thông báo kết quả")
    total_servers: int = Field(..., description="Tổng số servers sẽ scan")
    started_scans: List[int] = Field(..., description="Danh sách compliance_result IDs được tạo")


class ComplianceSearchParams(BaseModel):
    server_id: Optional[int] = Field(None, description="Filter theo server ID")
    workload_id: Optional[int] = Field(None, description="Filter theo workload ID")
    status: Optional[str] = Field(None, description="Filter theo trạng thái")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
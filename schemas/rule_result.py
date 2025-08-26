from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator

class RuleResultBase(BaseModel):
    rule_id: int = Field(..., description="ID của rule")
    rule_name: Optional[str] = Field(None, description="Tên rule")
    status: str = Field(..., description="Trạng thái rule: passed, failed, skipped, error")
    message: Optional[str] = Field(None, description="Thông báo kết quả")
    details: Optional[str] = Field(None, description="Chi tiết kết quả")
    execution_time: Optional[int] = Field(None, description="Thời gian thực thi (seconds)")
    output: Optional[Dict[str, Any]] = Field(None, description="Parsed output từ rule execution")

class RuleResultCreate(RuleResultBase):
    compliance_result_id: int = Field(..., description="ID của compliance result")

class RuleResultUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Trạng thái rule")
    message: Optional[str] = Field(None, description="Thông báo kết quả")
    details: Optional[str] = Field(None, description="Chi tiết kết quả")
    execution_time: Optional[int] = Field(None, description="Thời gian thực thi")
    output: Optional[Dict[str, Any]] = Field(None, description="Parsed output từ rule execution")

class RuleResultResponse(RuleResultBase):
    id: int
    compliance_result_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RuleResultListResponse(BaseModel):
    results: List[RuleResultResponse] = Field(..., description="Danh sách rule results")
    total: int = Field(..., description="Tổng số rule results")
    page: int = Field(..., description="Trang hiện tại")
    page_size: int = Field(..., description="Số mục trên mỗi trang")
    total_pages: int = Field(..., description="Tổng số trang")

    class Config:
        from_attributes = True
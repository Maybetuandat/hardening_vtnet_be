from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator

class RuleResultBase(BaseModel):
    
    status: str = Field(..., description="Trạng thái rule: passed, failed, skipped, error")
    message: Optional[str] = Field(None, description="Thông báo kết quả")
    details_error: Optional[str] = Field(None, description="Chi tiết kết quả")
    output: Optional[Dict[str, Any]] = Field(None, description="Parsed output từ rule execution")

class RuleResultCreate(RuleResultBase):
    compliance_result_id: int = Field(..., description="ID của compliance result")
    rule_id: int = Field(..., description="ID của rule")

class RuleResultUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Trạng thái rule")
    message: Optional[str] = Field(None, description="Thông báo kết quả")
    details: Optional[str] = Field(None, description="Chi tiết kết quả")
    execution_time: Optional[int] = Field(None, description="Thời gian thực thi")
    output: Optional[Dict[str, Any]] = Field(None, description="Parsed output từ rule execution")

class RuleResultResponse(RuleResultBase):
    id: int
    compliance_result_id: int
    rule_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    parameters: Optional[Dict[str, Any]] = Field(None, description="parameter in rule")


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
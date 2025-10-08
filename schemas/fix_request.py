# schemas/fix_request.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FixRequestCreate(BaseModel):
    """Schema tạo fix request mới"""
    rule_result_id: int = Field(..., description="ID của rule result cần fix")
    instance_id: int = Field(..., description="ID của instance")
    title: str = Field(..., min_length=5, max_length=255, description="Tiêu đề yêu cầu sửa")
    description: str = Field(..., min_length=10, description="Mô tả chi tiết")


class FixRequestApprove(BaseModel):
    """Schema admin approve/reject"""
    admin_comment: Optional[str] = Field(None, max_length=1000, description="Nhận xét của admin")


class FixRequestResponse(BaseModel):
    """Schema response"""
    id: int
    rule_result_id: int
    instance_id: int
    title: str
    description: str
    status: str
    created_by: str
    created_at: datetime
    admin_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    admin_comment: Optional[str] = None
    executed_at: Optional[datetime] = None
    execution_result: Optional[dict] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class FixRequestListResponse(BaseModel):
    """Schema list response"""
    requests: list[FixRequestResponse]
    total: int
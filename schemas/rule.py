from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, validator

class RuleBase(BaseModel):
    name: str = Field(..., max_length=100, description="Tên của rule")
    description: Optional[str] = Field(None, description="Mô tả về rule")
    severity: str = Field(..., description="Mức độ nghiêm trọng")
    workload_id: int = Field(..., description="ID của workload")
    parameters: Optional[Any] = Field(None, description="Tham số của rule dưới dạng JSON")
    is_active: bool = Field(True, description="Trạng thái hoạt động của rule")

    @validator('severity')
    def validate_severity(cls, v):
        allowed_severities = ["low", "medium", "high", "critical"]
        if v not in allowed_severities:
            raise ValueError(f'Severity phải là một trong: {", ".join(allowed_severities)}')
        return v

class RuleCreate(RuleBase):
    pass

class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Tên của rule")
    description: Optional[str] = Field(None, description="Mô tả về rule")
    severity: Optional[str] = Field(None, description="Mức độ nghiêm trọng")
    workload_id: Optional[int] = Field(None, description="ID của workload")
    parameters: Optional[Any] = Field(None, description="Tham số của rule dưới dạng JSON")
    is_active: Optional[bool] = Field(None, description="Trạng thái hoạt động của rule")

    @validator('severity')
    def validate_severity(cls, v):
        if v is not None:
            allowed_severities = ["low", "medium", "high", "critical"]
            if v not in allowed_severities:
                raise ValueError(f'Severity phải là một trong: {", ".join(allowed_severities)}')
        return v

class RuleResponse(RuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RuleListResponse(BaseModel):
    rules: List[RuleResponse]
    total_rules: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True

class RuleSearchParams(BaseModel):
    keyword: Optional[str] = None
    workload_id: Optional[int] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)

    
    
class WorkloadRuleCreate(BaseModel):
    """Rule create không cần workload_id vì sẽ được gán tự động"""
    name: str = Field(..., max_length=100, description="Tên của rule")
    description: Optional[str] = Field(None, description="Mô tả về rule")
    severity: str = Field(..., description="Mức độ nghiêm trọng: low, medium, high, critical")
    parameters: Optional[dict] = Field(None, description="Tham số của rule dưới dạng JSON")
    is_active: bool = Field(True, description="Trạng thái hoạt động của rule")
from datetime import datetime
from typing import Dict, List, Literal, Optional, Any
from click import command
from pydantic import BaseModel, Field, validator

class RuleBase(BaseModel):
    name: str = Field(..., max_length=100, description="Tên của rule")
    description: Optional[str] = Field(None, description="Mô tả về rule")
    workload_id: int = Field(..., description="ID của workload")
    parameters: Optional[Any] = Field(None, description="Tham số của rule dưới dạng JSON")
    is_active: bool = Field(True, description="Trạng thái hoạt động của rule")
    command: str = Field(..., description="Lệnh shell hoặc script để kiểm tra rule")

  

class RuleCreate(RuleBase):
    pass

class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Tên của rule")
    description: Optional[str] = Field(None, description="Mô tả về rule")
    workload_id: Optional[int] = Field(None, description="ID của workload")
    parameters: Optional[Any] = Field(None, description="Tham số của rule dưới dạng JSON")
    is_active: Optional[bool] = Field(None, description="Trạng thái hoạt động của rule")
    command: Optional[str] = Field(None, description="Lệnh shell hoặc script để kiểm tra rule")

    

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
    
    name: str = Field(..., max_length=100, description="Tên của rule")
    description: Optional[str] = Field(None, description="Mô tả về rule")
    parameters: Optional[dict] = Field(None, description="Tham số của rule dưới dạng JSON")
    is_active: bool = Field(True, description="Trạng thái hoạt động của rule")
class RuleCheckResult(BaseModel):
    
    name: str = Field(..., description="Tên rule")
    description: Optional[str] = Field(None, description="Mô tả rule")
    workload_id: int = Field(..., description="ID workload")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters JSON key-value")
    is_active: bool = Field(..., description="Trạng thái active")
    is_duplicate: bool = Field(..., description="Rule có trùng lặp không")
    duplicate_reason: Optional[Literal['name', 'parameter_hash']] = Field(None, description="Lý do trùng lặp")

    class Config:
        from_attributes = True
class RuleExistenceCheckRequest(BaseModel):
    workload_id: int
    rules: List[RuleCreate]
from datetime import datetime
from typing import Dict, List, Literal, Optional, Any
from click import command
from pydantic import BaseModel, Field, validator

class RuleBase(BaseModel):
    name: str = Field(..., max_length=100, description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    workload_id: Optional[int] = Field(None, description="Workload ID")
    parameters: Optional[Any] = Field(None, description="Rule parameters in JSON format")
    is_active: bool = Field(True, description="Rule active status")
    command: str = Field(..., description="Shell command or script to check rule")

  

class RuleCreate(RuleBase):
    pass

class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    workload_id: Optional[int] = Field(None, description="Workload ID")
    parameters: Optional[Any] = Field(None, description="Rule parameters in JSON format")
    is_active: Optional[bool] = Field(None, description="Rule active status")
    command: Optional[str] = Field(None, description="Shell command or script to check rule")

    

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

    

class RuleCheckResult(BaseModel):
    
    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    workload_id: int = Field(..., description="Workload ID")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters JSON key-value")
    is_active: bool = Field(..., description="Active status")
    is_duplicate: bool = Field(..., description="Whether rule is duplicate")
    duplicate_reason: Optional[Literal['name', 'parameter_hash']] = Field(None, description="Reason for duplication")
    command: str = Field(..., description="Shell command or script to check rule")

    class Config:
        from_attributes = True
class RuleExistenceCheckRequest(BaseModel):
    workload_id: int
    rules: List[RuleCreate]
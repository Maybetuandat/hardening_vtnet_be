
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime

class RuleChangeRequestCreate(BaseModel):
    """User tạo UPDATE request"""
    rule_id: int
    new_value: Dict[str, Any]

class RuleChangeRequestCreateNew(BaseModel):
    """User tạo CREATE request"""
    workload_id: int
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    command: str
    parameters: Optional[Dict[str, Any]] = None
    suggested_fix: Optional[str] = None
    is_active: Optional[str] = "active"

class RuleChangeRequestUpdate(BaseModel):
    """Admin approve/reject"""
    admin_note: Optional[str] = Field(None, max_length=500)

class RuleChangeRequestResponse(BaseModel):
    id: int
    workload_id: int
    rule_id: Optional[int]
    user_id: int
    request_type: Literal['create', 'update']
    old_value: Optional[Dict[str, Any]]
    new_value: Dict[str, Any]
    status: Literal['pending', 'approved', 'rejected']
    admin_id: Optional[int]
    admin_note: Optional[str]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]
    workload_name: Optional[str] = None
    rule_name: Optional[str] = None
    requester_username: Optional[str] = None
    admin_username: Optional[str] = None
    
    class Config:
        from_attributes = True

class RuleChangeRequestListResponse(BaseModel):
    requests: list[RuleChangeRequestResponse]
    total: int
    
    class Config:
        from_attributes = True
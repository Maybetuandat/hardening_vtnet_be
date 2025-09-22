# schemas/fix_action_log.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FixActionLogBase(BaseModel):
    user_id: int
    username: str
    rule_result_id: int
    compliance_result_id: int
    rule_name: Optional[str] = None
    old_status: str
    new_status: str
    command: Optional[str] = None
    execution_output: Optional[str] = None
    error_message: Optional[str] = None
    is_success: bool = True
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class FixActionLogCreate(FixActionLogBase):
    pass

class FixActionLogResponse(FixActionLogBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class FixActionLogListResponse(BaseModel):
    items: list[FixActionLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
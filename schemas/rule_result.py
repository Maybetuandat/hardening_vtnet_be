from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator

class RuleResultBase(BaseModel):
    status: str = Field(..., description="Rule status: passed, failed, skipped, error")
    message: Optional[str] = Field(None, description="Result message")
    details_error: Optional[str] = Field(None, description="Result details")
    output: Optional[Dict[str, Any]] = Field(None, description="Parsed output from rule execution")

class RuleResultCreate(RuleResultBase):
    compliance_result_id: int = Field(..., description="Compliance result ID")
    rule_id: int = Field(..., description="Rule ID")

class RuleResultUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Rule status")
    message: Optional[str] = Field(None, description="Result message")
    details: Optional[str] = Field(None, description="Result details")
    execution_time: Optional[int] = Field(None, description="Execution time")
    output: Optional[Dict[str, Any]] = Field(None, description="Parsed output from rule execution")

class RuleResultResponse(RuleResultBase):
    id: int
    compliance_result_id: int
    rule_name: Optional[str] = None
    rule_id: int
    created_at: datetime
    updated_at: datetime
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parameter in rule")


    class Config:
        from_attributes = True

class RuleResultListResponse(BaseModel):
    results: List[RuleResultResponse] = Field(..., description="List of rule results")
    total: int = Field(..., description="Total number of rule results")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        from_attributes = True
from typing import List, Optional
from pydantic import BaseModel, Field


class ServerFixRequest(BaseModel):
    instance_id: int = Field(..., description="Instance ID to apply fixes")
    rule_result_ids: List[int] = Field(..., description="List of rule result IDs to fix for this instance")


class SingleRuleFixResult(BaseModel):
    rule_result_id: int = Field(..., description="Rule result ID")
    rule_name: str = Field(..., description="Rule name")
    fix_command: Optional[str] = Field(None, description="Fix command executed")
    status: str = Field(..., description="Fix status: success, failed, skipped")
    message: str = Field(..., description="Result message")
    execution_output: Optional[str] = Field(None, description="Output from fix execution")
    error_details: Optional[str] = Field(None, description="Error details if any")
class ServerFixResponse(BaseModel):
    message: str = Field(..., description="Result message")
    instance_id: int = Field(..., description="Instance ID")
    instance_ip: str = Field(..., description="Instance IP address")
    total_fixes: int = Field(..., description="Total number of fixes attempted")
    successful_fixes: int = Field(..., description="Number of successful fixes")
    failed_fixes: int = Field(..., description="Number of failed fixes")
    skipped_fixes: int = Field(..., description="Number of skipped fixes (not needed or no fix command)")
    fix_details: List[SingleRuleFixResult] = Field(..., description="Detailed results for each rule result")



from typing import List, Optional
from pydantic import BaseModel, Field
from schemas.workload import WorkLoadCreate
from schemas.rule import RuleCreate
from schemas.command import CommandCreate

class WorkloadRuleCreate(BaseModel):
    """Rule create không cần workload_id vì sẽ được gán tự động"""
    name: str = Field(..., max_length=100, description="Tên của rule")
    description: Optional[str] = Field(None, description="Mô tả về rule")
    severity: str = Field(..., description="Mức độ nghiêm trọng: low, medium, high, critical")
    parameters: Optional[dict] = Field(None, description="Tham số của rule dưới dạng JSON")
    is_active: bool = Field(True, description="Trạng thái hoạt động của rule")

class WorkloadCommandCreate(BaseModel):
    """Command create với rule_index để tham chiếu đến rule trong danh sách"""
    rule_index: int = Field(..., description="Chỉ số rule trong danh sách (0-based)")
    os_version: str = Field(..., max_length=20, description="Phiên bản hệ điều hành")
    command_text: str = Field(..., description="Nội dung command hoặc Ansible command")
    is_active: bool = Field(True, description="Trạng thái hoạt động của command")

class WorkloadWithRulesAndCommandsRequest(BaseModel):
    workload: WorkLoadCreate
    rules: List[WorkloadRuleCreate]
    commands: List[WorkloadCommandCreate]

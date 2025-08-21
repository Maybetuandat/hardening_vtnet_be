# schemas/command.py - Enhanced version
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

class CommandBase(BaseModel):
    rule_id: int = Field(..., description="ID của rule")
    os_version: str = Field(..., max_length=20, description="Phiên bản hệ điều hành")
    command_text: str = Field(..., description="Nội dung command hoặc Ansible command")
    is_active: bool = Field(True, description="Trạng thái hoạt động của command")

    @validator('os_version')
    def validate_os_version(cls, v):
        if not v or not v.strip():
            raise ValueError('OS version không được để trống')
        return v.strip().lower()

    @validator('command_text')
    def validate_command_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Command text không được để trống')
        return v.strip()

class CommandCreate(BaseModel):
    """
    Enhanced CommandCreate để hỗ trợ tạo commands với workload
    """
    rule_id: Optional[int] = Field(None, description="ID của rule (có thể để trống khi tạo cùng workload)")
    rule_index: Optional[int] = Field(None, description="Chỉ số rule trong danh sách (0-based)")
    os_version: str = Field(..., max_length=20, description="Phiên bản hệ điều hành")
    command_text: str = Field(..., description="Nội dung command hoặc Ansible command")
    is_active: bool = Field(True, description="Trạng thái hoạt động của command")

    @validator('os_version')
    def validate_os_version(cls, v):
        if not v or not v.strip():
            raise ValueError('OS version không được để trống')
        return v.strip().lower()

    @validator('command_text')
    def validate_command_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Command text không được để trống')
        return v.strip()

class CommandUpdate(BaseModel):
    rule_id: Optional[int] = Field(None, description="ID của rule")
    os_version: Optional[str] = Field(None, max_length=20, description="Phiên bản hệ điều hành")
    command_text: Optional[str] = Field(None, description="Nội dung command hoặc Ansible command")
    is_active: Optional[bool] = Field(None, description="Trạng thái hoạt động của command")

    @validator('os_version')
    def validate_os_version(cls, v):
        if v is not None:
            if not v or not v.strip():
                raise ValueError('OS version không được để trống')
            return v.strip().lower()
        return v

    @validator('command_text')
    def validate_command_text(cls, v):
        if v is not None:
            if not v or not v.strip():
                raise ValueError('Command text không được để trống')
            return v.strip()
        return v

class CommandResponse(CommandBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CommandListResponse(BaseModel):
    commands: List[CommandResponse]
    total_commands: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True

class CommandSearchParams(BaseModel):
    keyword: Optional[str] = None
    rule_id: Optional[int] = None
    os_version: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)

    @validator('os_version')
    def validate_os_version(cls, v):
        if v is not None and v.strip():
            return v.strip().lower()
        return v

class WorkloadCommandCreate(BaseModel):
    """Command create với rule_index để tham chiếu đến rule trong danh sách"""
    rule_index: int = Field(..., description="Chỉ số rule trong danh sách (0-based)")
    os_version: str = Field(..., max_length=20, description="Phiên bản hệ điều hành")
    command_text: str = Field(..., description="Nội dung command hoặc Ansible command")
    is_active: bool = Field(True, description="Trạng thái hoạt động của command")
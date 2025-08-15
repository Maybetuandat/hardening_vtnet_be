from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class CommandCreate(BaseModel):
    rule_id: int
    os_version: str
    command_text: str
    is_active: Optional[bool] = True

    model_config = {"from_attributes": True}

    @field_validator('rule_id')
    @classmethod
    def validate_rule_id(cls, v):
        if v <= 0:
            raise ValueError('Rule ID must be greater than 0')
        return v

    @field_validator('os_version')
    @classmethod
    def validate_os_version(cls, v):
        if not v.strip():
            raise ValueError('OS version cannot be empty')
        if len(v.strip()) > 20:
            raise ValueError('OS version too long (max 20 characters)')
        valid_os_versions = ['centos', 'ubuntu', 'redhat', 'debian', 'rhel', 'suse', 'fedora']
        if v.strip().lower() not in valid_os_versions:
            raise ValueError(f'Invalid OS version. Must be one of: {", ".join(valid_os_versions)}')
        return v.strip().lower()

    @field_validator('command_text')
    @classmethod
    def validate_command_text(cls, v):
        if not v.strip():
            raise ValueError('Command text cannot be empty')
        return v.strip()


class CommandUpdate(BaseModel):
    rule_id: Optional[int] = None
    os_version: Optional[str] = None
    command_text: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}

    @field_validator('rule_id')
    @classmethod
    def validate_rule_id(cls, v):
        if v is not None:
            if v <= 0:
                raise ValueError('Rule ID must be greater than 0')
        return v

    @field_validator('os_version')
    @classmethod
    def validate_os_version(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('OS version cannot be empty')
            if len(v.strip()) > 20:
                raise ValueError('OS version too long (max 20 characters)')
            valid_os_versions = ['centos', 'ubuntu', 'redhat', 'debian', 'rhel', 'suse', 'fedora']
            if v.strip().lower() not in valid_os_versions:
                raise ValueError(f'Invalid OS version. Must be one of: {", ".join(valid_os_versions)}')
            return v.strip().lower()
        return v

    @field_validator('command_text')
    @classmethod
    def validate_command_text(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Command text cannot be empty')
            return v.strip()
        return v


class CommandResponse(BaseModel):
    id: int
    rule_id: int
    os_version: str
    command_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommandWithRuleResponse(BaseModel):
    """Command response with rule information"""
    id: int
    rule_id: int
    rule_name: Optional[str] = None
    rule_severity: Optional[str] = None
    os_version: str
    command_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
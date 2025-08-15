from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, field_validator


class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    severity: str = "medium"
    security_standard_id: int
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True

    model_config = {"from_attributes": True}

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v.strip()) > 100:
            raise ValueError('Name too long (max 100 characters)')
        return v.strip()

    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v):
        if not v.strip():
            raise ValueError('Severity cannot be empty')
        valid_severities = ['low', 'medium', 'high', 'critical']
        if v.strip().lower() not in valid_severities:
            raise ValueError(f'Invalid severity. Must be one of: {", ".join(valid_severities)}')
        return v.strip().lower()

    @field_validator('security_standard_id')
    @classmethod
    def validate_security_standard_id(cls, v):
        if v <= 0:
            raise ValueError('Security standard ID must be greater than 0')
        return v


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    security_standard_id: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Name cannot be empty')
            if len(v.strip()) > 100:
                raise ValueError('Name too long (max 100 characters)')
            return v.strip()
        return v

    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Severity cannot be empty')
            valid_severities = ['low', 'medium', 'high', 'critical']
            if v.strip().lower() not in valid_severities:
                raise ValueError(f'Invalid severity. Must be one of: {", ".join(valid_severities)}')
            return v.strip().lower()
        return v

    @field_validator('security_standard_id')
    @classmethod
    def validate_security_standard_id(cls, v):
        if v is not None:
            if v <= 0:
                raise ValueError('Security standard ID must be greater than 0')
        return v


class RuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    severity: str
    security_standard_id: int
    parameters: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RuleWithSecurityStandardResponse(BaseModel):
    """Rule response with security standard information"""
    id: int
    name: str
    description: Optional[str] = None
    severity: str
    security_standard_id: int
    security_standard_name: Optional[str] = None
    security_standard_version: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
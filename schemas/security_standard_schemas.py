from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class SecurityStandardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    version: Optional[str] = None
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

    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        if v is not None:
            if len(v.strip()) > 50:
                raise ValueError('Version too long (max 50 characters)')
            return v.strip() if v.strip() else None
        return v


class SecurityStandardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
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

    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        if v is not None:
            if len(v.strip()) > 50:
                raise ValueError('Version too long (max 50 characters)')
            return v.strip() if v.strip() else None
        return v


class SecurityStandardResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
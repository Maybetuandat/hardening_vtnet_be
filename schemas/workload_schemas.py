from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class WorkloadCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    workload_type: str
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

    @field_validator('workload_type')
    @classmethod
    def validate_workload_type(cls, v):
        if not v.strip():
            raise ValueError('Workload type cannot be empty')
        if len(v.strip()) > 100:
            raise ValueError('Workload type too long (max 100 characters)')
        valid_types = ['os', 'big_data', 'database', 'app']
        if v.strip().lower() not in valid_types:
            raise ValueError(f'Invalid workload type. Must be one of: {", ".join(valid_types)}')
        return v.strip()

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v):
        if v is not None:
            if len(v.strip()) > 150:
                raise ValueError('Display name too long (max 150 characters)')
            return v.strip() if v.strip() else None
        return v


class WorkloadUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    workload_type: Optional[str] = None
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

    @field_validator('workload_type')
    @classmethod
    def validate_workload_type(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Workload type cannot be empty')
            if len(v.strip()) > 100:
                raise ValueError('Workload type too long (max 100 characters)')
            valid_types = ['os', 'big_data', 'database', 'app']
            if v.strip().lower() not in valid_types:
                raise ValueError(f'Invalid workload type. Must be one of: {", ".join(valid_types)}')
            return v.strip()
        return v

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v):
        if v is not None:
            if len(v.strip()) > 150:
                raise ValueError('Display name too long (max 150 characters)')
            return v.strip() if v.strip() else None
        return v


class WorkloadResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    workload_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
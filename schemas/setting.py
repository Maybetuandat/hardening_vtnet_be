from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class SettingsBase(BaseModel):
    key: str = Field(..., max_length=100, description="Setting key")
    value: str = Field(..., description="Setting value")
    description: Optional[str] = Field(None, description="Setting description")
    is_active: bool = Field(default=True, description="Active status")


class SettingsCreate(SettingsBase):
    pass


class SettingsUpdate(BaseModel):
    value: Optional[str] = Field(None, description="Setting value")
    description: Optional[str] = Field(None, description="Setting description")
    is_active: Optional[bool] = Field(None, description="Active status")


class SettingsResponse(SettingsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanScheduleRequest(BaseModel):
    scan_time: str = Field(..., description="Scan time in HH:MM format (example: '00:00' for 12:00 AM)")
    is_enabled: bool = Field(default=True, description="Enable/disable automatic scan schedule")

    @validator('scan_time')
    def validate_scan_time(cls, v):
        try:
            parts = v.split(':')
            if len(parts) != 2:
                raise ValueError("Time format must be HH:MM")
            
            hour = int(parts[0])
            minute = int(parts[1])
            
            if not (0 <= hour <= 23):
                raise ValueError("Hour must be from 00 to 23")
            if not (0 <= minute <= 59):
                raise ValueError("Minute must be from 00 to 59")
                
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("Time must be numeric")
            raise e
            
        return v


class ScanScheduleResponse(BaseModel):
    scan_time: str
    is_enabled: bool
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    message: str
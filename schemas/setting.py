from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class SettingsBase(BaseModel):
    key: str = Field(..., max_length=100, description="Key của setting")
    value: str = Field(..., description="Giá trị setting")
    description: Optional[str] = Field(None, description="Mô tả setting")
    is_active: bool = Field(default=True, description="Trạng thái hoạt động")


class SettingsCreate(SettingsBase):
    pass


class SettingsUpdate(BaseModel):
    value: Optional[str] = Field(None, description="Giá trị setting")
    description: Optional[str] = Field(None, description="Mô tả setting")
    is_active: Optional[bool] = Field(None, description="Trạng thái hoạt động")


class SettingsResponse(SettingsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanScheduleRequest(BaseModel):
    scan_time: str = Field(..., description="Thời gian scan theo định dạng HH:MM (ví dụ: '00:00' cho 12:00 AM)")
    is_enabled: bool = Field(default=True, description="Bật/tắt lịch scan tự động")

    @validator('scan_time')
    def validate_scan_time(cls, v):
        try:
            parts = v.split(':')
            if len(parts) != 2:
                raise ValueError("Định dạng thời gian phải là HH:MM")
            
            hour = int(parts[0])
            minute = int(parts[1])
            
            if not (0 <= hour <= 23):
                raise ValueError("Giờ phải từ 00 đến 23")
            if not (0 <= minute <= 59):
                raise ValueError("Phút phải từ 00 đến 59")
                
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("Thời gian phải là số")
            raise e
            
        return v


class ScanScheduleResponse(BaseModel):
    scan_time: str
    is_enabled: bool
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    message: str
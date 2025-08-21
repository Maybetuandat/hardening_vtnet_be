from typing import Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re


class ServerBase(BaseModel):
    ip_address: str = Field(..., description="Địa chỉ IP của server")
    hostname: str = Field(..., max_length=255, description="Tên máy chủ")
    os_version: str = Field(..., max_length=50, description="Phiên bản hệ điều hành")
    ssh_port: int = Field(..., description="Cổng SSH của server")
    ssh_user: str = Field(..., max_length=100, description="Tên người dùng SSH")
    ssh_password: str = Field(..., description="Mật khẩu SSH của server")
    status: Optional[bool] = Field(None, description="Trạng thái của server")

    @validator('ip_address')
    def validate_ip_address(cls, v):
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Địa chỉ IP không hợp lệ')

class ServerCreate(ServerBase):
    workload_id: int = Field(..., description="ID của workload")

class ServerUpdate(BaseModel):
    hostname: Optional[str] = Field(None, max_length=255, description="Tên máy chủ") 
    ip_address: Optional[str] = Field(None, description="Địa chỉ IP của server")
    os_version: Optional[str] = Field(None, max_length=50, description="Phiên bản hệ điều hành")
    ssh_port: Optional[int] = Field(None, description="Cổng SSH của server")
    ssh_user: Optional[str] = Field(None, max_length=100, description="Tên người dùng SSH")
    ssh_password: Optional[str] = Field(None, description="Mật khẩu SSH của server")
    workload_id: Optional[int] = Field(None, description="ID của workload")  # Thêm field này

    @validator('ip_address')
    def validate_ip_address(cls, v):
        if v is not None:
            import ipaddress
            try:
                ipaddress.ip_address(v)
                return v
            except ValueError:
                raise ValueError('Địa chỉ IP không hợp lệ')
        return v

class ServerResponse(BaseModel):
    id: int
    hostname: str
    ip_address: str
    os_version: Optional[str]
    ssh_port: int
    ssh_user: Optional[str]
    ssh_password: Optional[str] = None  
    workload_id: int  
    
    created_at: datetime
    updated_at: datetime
    status: Optional[bool] = None

    class Config:
        from_attributes = True
class ServerListResponse(BaseModel):
    servers: list[ServerResponse]
    total_servers: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        from_attributes = True

class ServerSearchParams(BaseModel):
    keyword: Optional[str] = None
    workload_id: Optional[int] = None
    status: Optional[bool] = None
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)


class ServerUploadItem(BaseModel):
    """Schema cho từng server trong file Excel upload"""
    ip_address: str = Field(..., description="Địa chỉ IP của server")
    ssh_user: str = Field(..., description="SSH username")
    ssh_port: int = Field(22, description="SSH port")
    ssh_password: str = Field(..., description="SSH password")
    workload_name: str = Field(..., description="Tên workload")
    hostname: Optional[str] = Field(None, description="Hostname (auto-detect nếu để trống)")
    os_version: Optional[str] = Field(None, description="OS version (auto-detect nếu để trống)")
    
    @validator('ip_address')
    def validate_ip(cls, v):
        # Validate IP format
        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if not re.match(ip_pattern, v):
            raise ValueError('IP address không hợp lệ')
        return v
    
    @validator('ssh_port')
    def validate_ssh_port(cls, v):
        if v < 1 or v > 65535:
            raise ValueError('SSH port phải trong khoảng 1-65535')
        return v
    
    @validator('workload_name')
    def validate_workload_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Workload name không được để trống')
        return v.strip()

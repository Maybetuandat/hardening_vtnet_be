from pydantic import BaseModel, Field, validator
from datetime import datetime

class ServerBase(BaseModel):
    ip_address: str = Field(..., description="Địa chỉ IP của server")
    os_version: str = Field(..., max_length=50, description="Phiên bản hệ điều hành")
    ssh_port: int = Field(..., description="Cổng SSH của server")
    ssh_user: str = Field(..., max_length=100, description="Tên người dùng SSH")
    ssh_password: str = Field(..., description="Mật khẩu SSH của server")

    @validator('ip_address')
    def validate_ip_address(cls, v):
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Địa chỉ IP không hợp lệ')
class ServerCreate(ServerBase):
    pass
class ServerUpdate(BaseModel):
    ip_address: str = Field(None, description="Địa chỉ IP của server")
    os_version: str = Field(None, max_length=50, description="Phiên bản hệ điều hành")
    ssh_port: int = Field(None, description="Cổng SSH của server")
    ssh_user: str = Field(None, max_length=100, description="Tên người dùng SSH")
    ssh_password: str = Field(None, description="Mật khẩu SSH của server")

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
class ServerResponse(ServerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ServerListResponse(BaseModel):
    servers: list[ServerResponse]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        from_attributes = True
class ServerWithWorkload(ServerResponse):
    workload: Optional[dict] = None

    class Config:
        from_attributes = True
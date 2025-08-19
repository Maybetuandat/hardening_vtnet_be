from typing import List, Optional
from pydantic import BaseModel, Field, validator
import ipaddress

class ServerConnectionInfo(BaseModel):
    ip: str = Field(..., description="Địa chỉ IP của server")
    ssh_user: str = Field(..., description="Tên người dùng SSH")
    ssh_password: str = Field(..., description="Mật khẩu SSH")
    ssh_port: int = Field(22, description="Cổng SSH (mặc định 22)")
    
    @validator('ip')
    def validate_ip_address(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Địa chỉ IP không hợp lệ')

class TestConnectionRequest(BaseModel):
    servers: List[ServerConnectionInfo] = Field(..., description="Danh sách server cần test connection")

class ServerConnectionResult(BaseModel):
    ip: str
    ssh_user: str
    ssh_port: int
    status: str  # success, failed
    message: str
    hostname: Optional[str] = None
    os_version: Optional[str] = None
    response_time: Optional[float] = None  # in milliseconds
    error_details: Optional[str] = None

class TestConnectionResponse(BaseModel):
    total_servers: int
    successful_connections: int
    failed_connections: int
    results: List[ServerConnectionResult]
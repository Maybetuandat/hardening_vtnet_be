from typing import List, Optional
from pydantic import BaseModel, Field, validator
import ipaddress

class ServerConnectionInfo(BaseModel):
    ip: str = Field(..., description="Server IP address")
    ssh_user: str = Field(..., description="SSH username")
    ssh_password: str = Field(..., description="SSH password")
    ssh_port: int = Field(22, description="SSH port (default 22)")
    
    @validator('ip')
    def validate_ip_address(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address')

class TestConnectionRequest(BaseModel):
    servers: List[ServerConnectionInfo] = Field(..., description="List of servers to test connection")

class ServerConnectionResult(BaseModel):
    ip: str = Field(..., description="Server IP address")
    ssh_user: str = Field(..., description="SSH username")
    ssh_port: int = Field(..., description="SSH port")
    status: str = Field(..., description="Connection status: success, failed")
    message: str = Field(..., description="Connection result message")
    hostname: Optional[str] = Field(None, description="Server hostname")
    os_version: Optional[str] = Field(None, description="Operating system version")
    error_details: Optional[str] = Field(None, description="Error details if connection failed")

class TestConnectionResponse(BaseModel):
    total_servers: int = Field(..., description="Total number of servers tested")
    successful_connections: int = Field(..., description="Number of successful connections")
    failed_connections: int = Field(..., description="Number of failed connections")
    results: List[ServerConnectionResult] = Field(..., description="Detailed connection results")
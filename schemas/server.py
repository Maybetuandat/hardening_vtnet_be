from typing import Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re

from models import user


class ServerBase(BaseModel):
    ip_address: str = Field(..., description="Ip server")
    hostname: str = Field(..., max_length=255, description="Hostname of server")
    os_version: str = Field(..., max_length=50, description="Os version of server")
   
    status: Optional[bool] = Field(None, description="Server status")
    user_id: Optional[int] = Field(None, description="Id user manage server")
    @validator('ip_address')
    def validate_ip_address(cls, v):
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Ip address is not valid')

class ServerCreate(ServerBase):
    workload_id: int = Field(..., description="ID của workload")

class ServerUpdate(BaseModel):
    hostname: Optional[str] = Field(None, max_length=255, description="Hostname of server") 
    ip_address: Optional[str] = Field(None, description="Ip server")
    os_version: Optional[str] = Field(None, max_length=50, description="Os version of server")
    ssh_port: Optional[int] = Field(None, description="Ssh port")
   
    workload_id: Optional[int] = Field(None, description="Workload id") 
    user_id:Optional[int] = Field(None, description="update user id ")

    @validator('ip_address')
    def validate_ip_address(cls, v):
        if v is not None:
            import ipaddress
            try:
                ipaddress.ip_address(v)
                return v
            except ValueError:
                raise ValueError('Ip address is not validate')
        return v

class ServerResponse(BaseModel):
    id: int
    hostname: str
    ip_address: str
    os_version: Optional[str]
    ssh_port: int

    workload_id: int  
    workload_name: Optional[str] = None  
    created_at: datetime
    updated_at: datetime
    status: Optional[bool] = None
    nameofmanager: Optional[str] = None
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
    user_id: Optional[int] = None


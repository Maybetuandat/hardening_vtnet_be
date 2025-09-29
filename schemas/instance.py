from typing import Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re

from models import user
from schemas.os import OsResponseFromDcim
from schemas.user import  UserResponseFromDcim


class InstanceBase(BaseModel):
    name: str = Field(..., max_length=255, description="Ip instance")   
    status: Optional[bool] = Field(None, description="Instance status")
    user_id: Optional[int] = Field(None, description="Id user manage instance")
    @validator('name')
    def validate_ip_address(cls, v):
        import ipaddress
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Ip address is not valid')

class InstanceCreate(InstanceBase):
    workload_id: Optional[int] = Field(None, description="Workload Id ")

class InstanceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="Ip instance") 
    ssh_port: Optional[int] = Field(None, description="Ssh port")
   
    workload_id: Optional[int] = Field(None, description="Workload id") 
    user_id:Optional[int] = Field(None, description="update user id ")

    @validator('name')
    def validate_ip_address(cls, v):
        if v is not None:
            import ipaddress
            try:
                ipaddress.ip_address(v)
                return v
            except ValueError:
                raise ValueError('Ip address is not validate')
        return v

class InstanceResponse(BaseModel):
    id: int
    name: str
    ssh_port: int

    workload_id: Optional[int]  
    workload_name: Optional[str] = None  
    created_at: datetime
    updated_at: datetime
    status: Optional[bool] = None
    nameofmanager: Optional[str] = None
class InstanceListResponse(BaseModel):
    instances: list[InstanceResponse]
    total_instances: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        from_attributes = True

class InstanceSearchParams(BaseModel):
    keyword: Optional[str] = None
    workload_id: Optional[int] = None
    status: Optional[bool] = None
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)
    user_id: Optional[int] = None

class InstanceResponseFromDcim(BaseModel):
    id : int 
    name : str
    user: UserResponseFromDcim
    os: OsResponseFromDcim
class InstanceListResponseFromDcim(BaseModel):
    instances: list[InstanceResponseFromDcim]
    total_instances: int
    page: int
    page_size: int
    total: int
    total_pages: int
    
    class Config:
        from_attributes = True
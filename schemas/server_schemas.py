from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, validator
import ipaddress


class ServerCreate(BaseModel):
    name: str
    hostname: str
    ip_address: str
    workload_id: int
    server_role: Optional[str] = None
    os_type: str
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    environment: str
    status: str
  
    ssh_port: Optional[int] = 22
    ssh_key_id: Optional[int] = None
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

    @field_validator('hostname')
    @classmethod
    def validate_hostname(cls, v):
        if not v.strip():
            raise ValueError('Hostname cannot be empty')
        if len(v.strip()) > 255:
            raise ValueError('Hostname too long (max 255 characters)')
        # Basic hostname validation
        hostname = v.strip().lower()
        if not hostname.replace('-', '').replace('.', '').isalnum():
            raise ValueError('Hostname contains invalid characters')
        return hostname

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v):
        if not v.strip():
            raise ValueError('IP address cannot be empty')
        try:
            ipaddress.ip_address(v.strip())
        except ValueError:
            raise ValueError('Invalid IP address format')
        return v.strip()

    @field_validator('os_type')
    @classmethod
    def validate_os_type(cls, v):
        if not v.strip():
            raise ValueError('OS type cannot be empty')
        valid_os_types = ['linux', 'windows', 'unix', 'macos']
        if v.strip().lower() not in valid_os_types:
            raise ValueError(f'Invalid OS type. Must be one of: {", ".join(valid_os_types)}')
        return v.strip().lower()

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        if not v.strip():
            raise ValueError('Environment cannot be empty')
        valid_environments = ['production', 'staging', 'development', 'testing']
        if v.strip().lower() not in valid_environments:
            raise ValueError(f'Invalid environment. Must be one of: {", ".join(valid_environments)}')
        return v.strip().lower()

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if not v.strip():
            raise ValueError('Status cannot be empty')
        valid_statuses = ['online', 'offline', 'maintenance', 'error', 'unknown']
        if v.strip().lower() not in valid_statuses:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
        return v.strip().lower()

    @field_validator('ssh_port')
    @classmethod
    def validate_ssh_port(cls, v):
        if v is not None:
            if v < 1 or v > 65535:
                raise ValueError('SSH port must be between 1 and 65535')
        return v

  

    @field_validator('cpu_cores')
    @classmethod
    def validate_cpu_cores(cls, v):
        if v is not None:
            if v < 1:
                raise ValueError('CPU cores must be greater than 0')
        return v

    @field_validator('memory_gb')
    @classmethod
    def validate_memory_gb(cls, v):
        if v is not None:
            if v <= 0:
                raise ValueError('Memory must be greater than 0 GB')
        return v


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    workload_id: Optional[int] = None
    server_role: Optional[str] = None
    os_type: Optional[str] = None
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    environment: Optional[str] = None
    status: Optional[str] = None
  
    ssh_port: Optional[int] = None
    ssh_key_id: Optional[int] = None
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

    @field_validator('hostname')
    @classmethod
    def validate_hostname(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Hostname cannot be empty')
            if len(v.strip()) > 255:
                raise ValueError('Hostname too long (max 255 characters)')
            hostname = v.strip().lower()
            if not hostname.replace('-', '').replace('.', '').isalnum():
                raise ValueError('Hostname contains invalid characters')
            return hostname
        return v

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('IP address cannot be empty')
            try:
                ipaddress.ip_address(v.strip())
            except ValueError:
                raise ValueError('Invalid IP address format')
            return v.strip()
        return v

    @field_validator('os_type')
    @classmethod
    def validate_os_type(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('OS type cannot be empty')
            valid_os_types = ['linux', 'windows', 'unix', 'macos']
            if v.strip().lower() not in valid_os_types:
                raise ValueError(f'Invalid OS type. Must be one of: {", ".join(valid_os_types)}')
            return v.strip().lower()
        return v

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Environment cannot be empty')
            valid_environments = ['production', 'staging', 'development', 'testing']
            if v.strip().lower() not in valid_environments:
                raise ValueError(f'Invalid environment. Must be one of: {", ".join(valid_environments)}')
            return v.strip().lower()
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Status cannot be empty')
            valid_statuses = ['online', 'offline', 'maintenance', 'error', 'unknown']
            if v.strip().lower() not in valid_statuses:
                raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
            return v.strip().lower()
        return v

    @field_validator('ssh_port')
    @classmethod
    def validate_ssh_port(cls, v):
        if v is not None:
            if v < 1 or v > 65535:
                raise ValueError('SSH port must be between 1 and 65535')
        return v

   

    @field_validator('cpu_cores')
    @classmethod
    def validate_cpu_cores(cls, v):
        if v is not None:
            if v < 1:
                raise ValueError('CPU cores must be greater than 0')
        return v

    @field_validator('memory_gb')
    @classmethod
    def validate_memory_gb(cls, v):
        if v is not None:
            if v <= 0:
                raise ValueError('Memory must be greater than 0 GB')
        return v


class ServerResponse(BaseModel):
    id: int
    name: str
    hostname: str
    ip_address: str
    workload_id: int
    server_role: Optional[str] = None
    os_type: str
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    environment: str
    status: str
 
    ssh_port: int
    ssh_key_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
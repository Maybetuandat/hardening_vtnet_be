from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

import re

from models.ssh_key import SshKeyType







class SshKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    key_type: SshKeyType
    public_key: str
    private_key: str
    
    @field_validator('public_key')
    @classmethod
    def validate_public_key(cls, v):
        if not v.strip():
            raise ValueError('Public key cannot be empty')
        
        # format validaytion of ssh public key 
        ssh_key_pattern = r'^(ssh-rsa|ssh-ed25519|ecdsa-sha2-|ssh-dss)\s+[A-Za-z0-9+/]+[=]{0,2}(\s+.*)?$'
        if not re.match(ssh_key_pattern, v.strip()):
            raise ValueError('Invalid SSH public key format')
        
        return v.strip()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v.strip()) > 100:
            raise ValueError('Name too long (max 100 characters)')
        return v.strip()

    @field_validator('private_key')
    @classmethod
    def validate_private_key(cls, v):
        if not v.strip():
            raise ValueError('Private key cannot be empty')
        
        # format validation of ssh private key - more flexible pattern
        v_stripped = v.strip()
        
        # Check if it starts with BEGIN and ends with END
        if not (v_stripped.startswith('-----BEGIN') and v_stripped.endswith('-----')):
            raise ValueError('Invalid SSH private key format')
        
        # Check for common private key types
        valid_key_types = ['RSA PRIVATE KEY', 'OPENSSH PRIVATE KEY', 'EC PRIVATE KEY', 'DSA PRIVATE KEY']
        has_valid_type = any(key_type in v_stripped for key_type in valid_key_types)
        
        if not has_valid_type:
            raise ValueError('Invalid SSH private key format')
        
        return v_stripped

class SshKeyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    public_key: Optional[str] = None
    private_key: Optional[str] = None
    key_type: Optional[SshKeyType] = None
    
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

class SshKeyUpdateResponse(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    key_type: Optional[SshKeyType] = None
    
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
class SshKeyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    key_type: SshKeyType
    public_key: str
    private_key: Optional[str] = None
    fingerprint: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

   
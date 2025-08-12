from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

import re

from models.ssh_key import SSHKeyType



class SshKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    key_type: SSHKeyType
    public_key: str
    private_key: str
    
    @validator('public_key')
    def validate_public_key(cls, v):
        if not v.strip():
            raise ValueError('Public key cannot be empty')
        
        # format validaytion of ssh public key 
        ssh_key_pattern = r'^(ssh-rsa|ssh-ed25519|ecdsa-sha2-|ssh-dss)\s+[A-Za-z0-9+/]+[=]{0,2}(\s+.*)?$'
        if not re.match(ssh_key_pattern, v.strip()):
            raise ValueError('Invalid SSH public key format')
        
        return v.strip()
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v.strip()) > 100:
            raise ValueError('Name too long (max 100 characters)')
        return v.strip()

    @validator('private_key')
    def validate_private_key(cls, v):
        if not v.strip():
            raise ValueError('Private key cannot be empty')
        
        # format validation of ssh private key
        ssh_private_key_pattern = r'^(-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----\n[^\n]+\n-----END \2 PRIVATE KEY-----)$'
        if not re.match(ssh_private_key_pattern, v.strip()):
            raise ValueError('Invalid SSH private key format')
        
        return v.strip()

class SshKeyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('name')
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
    key_type: SSHKeyType
    public_key: str
    private_key: Optional[str] = None
    fingerprint: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True  # Enable ORM mode for compatibility with SQLAlchemy models

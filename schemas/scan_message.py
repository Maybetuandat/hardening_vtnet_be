# hardening_backend/schemas/scan_message.py
# scan_service/schemas/scan_message.py (copy y hệt)

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RuleInfo(BaseModel):
    """Thông tin rule đầy đủ để thực thi scan"""
    id: int
    name: str
    command: str
    parameters: Optional[Dict[str, Any]] = None
    suggested_fix: Optional[str] = None
    description: Optional[str] = None


class InstanceCredentials(BaseModel):
    """Thông tin credentials để SSH"""
    username: Optional[str] = None
    password: Optional[str] = None
    


class ScanInstanceMessage(BaseModel):
    """
    Message đầy đủ để scan service thực thi scan
    Chứa TẤT CẢ thông tin cần thiết, không cần query database
    """
    # Instance info
    instance_id: int
    instance_name: str  # IP address
    ssh_port: int
    instance_role: Optional[str] = None
    
    # Workload info
    workload_id: int
    workload_name: str
    workload_description: Optional[str] = None
    
    # OS info
    os_id: int
    os_name: str
    os_type: int
    os_display: str
    
    # User info
    user_id: int
    
    # Rules - đầy đủ thông tin để execute
    rules: List[RuleInfo]
    
    # Credentials - LẤY TỪ USER
    credentials: InstanceCredentials
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    scan_request_id: Optional[str] = None
    
    class Config:
        from_attributes = True
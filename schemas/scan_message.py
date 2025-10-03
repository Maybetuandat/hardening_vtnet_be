# schemas/scan_message.py

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RuleInfo(BaseModel):
    """Thông tin rule đầy đủ để thực thi scan"""
    id: int
    name: str
    command: str
    parameters: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class InstanceCredentials(BaseModel):
    """Thông tin credentials để SSH"""
    username: Optional[str] = None
    password: Optional[str] = None
    
    class Config:
        from_attributes = True


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


class RuleResultInfo(BaseModel):
    """Thông tin kết quả của một Rule sau khi thực thi, không có liên kết DB"""
    rule_id: int
    status: str  # "passed", "failed"
    message: str
    details_error: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class ScanResponseMessage(BaseModel):
    """Message phản hồi sau khi một instance được quét xong"""
    scan_request_id: Optional[str]  # Liên kết với request ban đầu
    instance_id: int
    instance_name: str
    workload_id: int
    user_id: int
    
    status: str  # "completed", "failed" (tổng thể của instance)
    detail_error: Optional[str] = None  # Lỗi tổng thể nếu không thể quét
    
    total_rules: int
    rules_passed: int
    rules_failed: int
    
    rule_results: List[RuleResultInfo] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True
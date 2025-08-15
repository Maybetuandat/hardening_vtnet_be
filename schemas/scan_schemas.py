# schemas/scan_schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ScanType(str, Enum):
    SIMPLE = "simple"
    COMPLIANCE = "compliance"


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class RuleStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


# Request Schemas
class SimpleScanRequest(BaseModel):
    server_id: int = Field(..., gt=0, description="ID của server cần scan")
    
    @field_validator('server_id')
    @classmethod
    def validate_server_id(cls, v):
        if v <= 0:
            raise ValueError('Server ID must be greater than 0')
        return v


class ComplianceScanRequest(BaseModel):
    server_id: int = Field(..., gt=0, description="ID của server cần scan")
    security_standard_id: int = Field(..., gt=0, description="ID của security standard")
    
    @field_validator('server_id', 'security_standard_id')
    @classmethod
    def validate_ids(cls, v):
        if v <= 0:
            raise ValueError('ID must be greater than 0')
        return v


class TestConnectionRequest(BaseModel):
    server_id: int = Field(..., gt=0, description="ID của server cần test connection")


# Response Schemas
class CommandResult(BaseModel):
    command: str
    description: str
    output: str
    error: Optional[str] = None
    return_code: int
    success: bool
    execution_time: Optional[float] = None


class SimpleScanResult(BaseModel):
    server_id: int
    server_name: str
    ip_address: str
    scan_time: str
    scan_type: str
    results: Dict[str, CommandResult]
    total_commands: int
    successful_commands: int
    failed_commands: int


class RuleResultDetail(BaseModel):
    rule_id: int
    rule_name: str
    rule_description: Optional[str] = None
    severity: str
    status: RuleStatus
    message: Optional[str] = None
    details: Optional[List[Dict[str, Any]]] = None
    created_at: str


class ComplianceScanResult(BaseModel):
    compliance_result_id: int
    server_id: int
    server_name: str
    security_standard_id: int
    security_standard_name: str
    scan_time: str
    status: ScanStatus
    total_rules: int
    passed_rules: int
    failed_rules: int
    skipped_rules: int
    score: int
    rule_results: List[RuleResultDetail]


class ScanResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ConnectionTestResult(BaseModel):
    server_id: int
    connection_status: str
    successful_commands: int
    total_commands: int
    errors: Optional[List[str]] = None
    response_time: Optional[float] = None


class ScanHistoryItem(BaseModel):
    compliance_result_id: int
    security_standard_name: str
    security_standard_version: Optional[str] = None
    status: ScanStatus
    total_rules: int
    passed_rules: int
    failed_rules: int
    score: int
    scan_date: str
    created_at: str


class ScanHistoryResponse(BaseModel):
    server_id: int
    total: int
    results: List[ScanHistoryItem]
    pagination: Dict[str, Any]


# Configuration Schemas
class ParameterComparison(BaseModel):
    expected_return_code: Optional[int] = 0
    expected_contains: Optional[str] = None
    expected_pattern: Optional[str] = None
    expected_min: Optional[float] = None
    expected_max: Optional[float] = None
    expected_equals: Optional[str] = None
    case_sensitive: bool = True


class RuleParameters(BaseModel):
    """Schema cho parameters của Rule"""
    comparison: Optional[ParameterComparison] = None
    additional_checks: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = 30
    retry_count: Optional[int] = 1


# Ansible Schemas
class AnsibleTaskResult(BaseModel):
    task_name: str
    status: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    return_code: Optional[int] = None
    changed: bool = False
    failed: bool = False
    skipped: bool = False


class AnsiblePlaybookResult(BaseModel):
    playbook_name: str
    host: str
    status: str
    tasks: List[AnsibleTaskResult]
    execution_time: Optional[float] = None
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    changed_tasks: int


# Export/Report Schemas
class ReportFilter(BaseModel):
    server_ids: Optional[List[int]] = None
    security_standard_ids: Optional[List[int]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    status: Optional[List[ScanStatus]] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None


class ReportRequest(BaseModel):
    filters: Optional[ReportFilter] = None
    format: str = Field(default="pdf", regex="^(pdf|excel|csv|json)$")
    include_details: bool = True
    include_remediation: bool = False


class ReportResponse(BaseModel):
    report_id: str
    status: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    created_at: str
    expires_at: Optional[str] = None


# SSH Key Validation Schemas
class SSHKeyValidation(BaseModel):
    name: str
    description: Optional[str] = None
    key_type: str
    public_key: str
    private_key: str
    fingerprint: str
    is_active: bool = True


# Server Connection Schemas
class ServerConnectionInfo(BaseModel):
    server_id: int
    hostname: str
    ip_address: str
    ssh_port: int
    ssh_key_id: Optional[int] = None
    os_type: str
    os_version: Optional[str] = None
    status: str


# Error Schemas
class ScanError(BaseModel):
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ValidationError(BaseModel):
    field: str
    message: str
    code: str


# Batch Operation Schemas
class BatchScanRequest(BaseModel):
    server_ids: List[int] = Field(..., min_items=1, max_items=50)
    security_standard_id: int = Field(..., gt=0)
    parallel_limit: int = Field(default=5, ge=1, le=10)
    
    @field_validator('server_ids')
    @classmethod
    def validate_server_ids(cls, v):
        if not v:
            raise ValueError('At least one server ID is required')
        if len(v) > 50:
            raise ValueError('Maximum 50 servers allowed per batch')
        if len(set(v)) != len(v):
            raise ValueError('Duplicate server IDs are not allowed')
        return v


class BatchScanResponse(BaseModel):
    batch_id: str
    total_servers: int
    status: str
    started_at: str
    estimated_completion: Optional[str] = None
    server_statuses: List[Dict[str, Any]]


# Notification Schemas
class NotificationConfig(BaseModel):
    enabled: bool = True
    email_recipients: Optional[List[str]] = None
    webhook_url: Optional[str] = None
    notify_on_completion: bool = True
    notify_on_failure: bool = True
    notify_on_critical_findings: bool = True
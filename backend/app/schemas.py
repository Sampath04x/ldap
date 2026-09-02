from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Optional, Generic, TypeVar, Literal
from datetime import datetime
from uuid import UUID

T = TypeVar('T')

class UserSummary(BaseModel):
    id: UUID
    username: str
    email: str
    display_name: str
    status: str
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    display_name: str
    department: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    status: str
    ldap_dn: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class GroupSummary(BaseModel):
    id: UUID
    group_name: str
    display_name: Optional[str] = None
    status: str
    model_config = ConfigDict(from_attributes=True)

class GroupResponse(BaseModel):
    id: UUID
    group_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    status: str
    ldap_dn: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class FirewallSummary(BaseModel):
    id: UUID
    hostname: str
    ip_address: str
    environment: str
    status: str
    model_config = ConfigDict(from_attributes=True)

class FirewallResponse(BaseModel):
    id: UUID
    hostname: str
    ip_address: str
    model: Optional[str] = None
    software_version: Optional[str] = None
    environment: str
    location: Optional[str] = None
    status: str
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class LDAPServerResponse(BaseModel):
    id: UUID
    firewall_id: UUID
    profile_name: str
    server_host: str
    server_port: int
    use_tls: bool
    base_dn: Optional[str] = None
    status: str
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserIPMappingResponse(BaseModel):
    id: int
    user_id: UUID
    firewall_id: UUID
    ip_address: str
    mapped_at: datetime
    expires_at: Optional[datetime] = None
    is_current: bool
    source: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AuthEventResponse(BaseModel):
    id: int
    user_id: Optional[UUID] = None
    firewall_id: UUID
    username_raw: str
    source_ip: Optional[str] = None
    result: str
    failure_reason: Optional[str] = None
    auth_method: Optional[str] = None
    occurred_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SearchItem(BaseModel):
    type: str
    score: float
    data: dict

class SearchResult(BaseModel):
    items: list[SearchItem]
    total: int
    page: int
    page_size: int
    has_more: bool

class DiagnosticUserRequest(BaseModel):
    firewall_id: UUID
    username: str

CheckStatus = Literal['PASSED', 'FAILED', 'WARNING', 'SKIPPED']
DiagnosticSeverity = Literal['critical', 'high', 'medium', 'info']

class DiagnosticCheck(BaseModel):
    name: str = Field(..., description="Check name")
    passed: bool
    status: CheckStatus = Field('PASSED')
    code: str = Field(..., description="Diagnostic code")
    severity: DiagnosticSeverity
    detail: str = Field(..., description="Message detail")
    evidence: Optional[str] = ""
    action: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class DiagnosticRunResponse(BaseModel):
    run_id: UUID
    subject: str
    firewall: str
    overall_result: str
    overall_status: str
    duration_ms: Optional[int] = None
    checks: list[DiagnosticCheck]
    summary: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class KeysetCursor(BaseModel):
    after_id: Optional[int] = None
    after_ts: Optional[datetime] = None

class PagedResponse(BaseModel, Generic[T]):
    items: list[T]
    has_more: bool
    next_cursor: Optional[KeysetCursor] = None

class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail

class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    provider: str
    version: str

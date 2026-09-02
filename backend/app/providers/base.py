from typing import Protocol, runtime_checkable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FirewallStatus:
    reachable: bool
    status: str  # 'reachable'|'unreachable'|'degraded'|'unknown'
    last_seen_at: datetime | None
    detail: str

@dataclass
class UserIdentity:
    found: bool
    username: str
    status: str  # 'active'|'inactive'|'disabled'|'locked'
    display_name: str
    ldap_dn: str | None
    detail: str

@dataclass
class IPMapping:
    ip_address: str
    mapped_at: datetime
    is_current: bool
    source: str | None
    age_hours: float

@dataclass
class LDAPConfig:
    profile_name: str
    server_host: str
    server_port: int
    use_tls: bool
    base_dn: str | None
    bind_dn: str | None

@dataclass
class LDAPConnResult:
    reachable: bool
    status: str  # 'reachable'|'unreachable'|'tls_error'|'misconfigured'|'unknown'
    detail: str

@dataclass
class GroupMappingState:
    mapped_groups: list[str]
    last_synced_at: datetime | None
    age_hours: float | None
    status: str  # 'active'|'stale'|'empty'|'error'

@runtime_checkable
class PaloAltoProvider(Protocol):
    async def get_firewall_status(self, firewall_id: str) -> FirewallStatus: ...
    async def get_user_identity(self, username: str, firewall_id: str) -> UserIdentity: ...
    async def get_user_ip_mappings(self, username: str, firewall_id: str) -> list[IPMapping]: ...
    async def get_ldap_configs(self, firewall_id: str) -> list[LDAPConfig]: ...
    async def test_ldap_connectivity(self, firewall_id: str, profile: str) -> LDAPConnResult: ...
    async def get_user_groups(self, username: str, firewall_id: str) -> list[str]: ...
    async def get_group_mapping_state(self, firewall_id: str) -> GroupMappingState: ...

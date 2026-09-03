from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, DateTime, JSON, ForeignKey, CheckConstraint, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    department = Column(String(128), nullable=True)
    job_title = Column(String(128), nullable=True)
    location = Column(String(128), nullable=True)
    status = Column(String(16), nullable=False, server_default='active')
    ldap_dn = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("status IN ('active','inactive','disabled','locked')"),)

class Group(Base):
    __tablename__ = 'groups'
    id = Column(UUID(as_uuid=True), primary_key=True)
    group_name = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(16), server_default='active')
    ldap_dn = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("status IN ('active','disabled')"),)

class UserGroupMembership(Base):
    __tablename__ = 'user_group_memberships'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey('groups.id', ondelete='CASCADE'), nullable=False)
    source = Column(String(32), nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        CheckConstraint("source IN ('ldap','manual','sync')"),
        UniqueConstraint('user_id', 'group_id')
    )

class Firewall(Base):
    __tablename__ = 'firewalls'
    id = Column(UUID(as_uuid=True), primary_key=True)
    hostname = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=False)
    model = Column(String(64), nullable=True)
    software_version = Column(String(32), nullable=True)
    environment = Column(String(32), server_default='production')
    location = Column(String(128), nullable=True)
    status = Column(String(16), server_default='unknown')
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("environment IN ('production','staging','lab')"),
        CheckConstraint("status IN ('reachable','unreachable','degraded','unknown')")
    )

class LDAPServer(Base):
    __tablename__ = 'ldap_servers'
    id = Column(UUID(as_uuid=True), primary_key=True)
    firewall_id = Column(UUID(as_uuid=True), ForeignKey('firewalls.id', ondelete='CASCADE'), nullable=False)
    profile_name = Column(String(128), nullable=False)
    server_host = Column(String(255), nullable=False)
    server_port = Column(Integer, server_default='389')
    use_tls = Column(Boolean, nullable=False, server_default='false')
    base_dn = Column(Text, nullable=True)
    bind_dn = Column(Text, nullable=True)
    status = Column(String(16), server_default='unknown')
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("server_port >= 1 AND server_port <= 65535"),
        CheckConstraint("status IN ('reachable','unreachable','tls_error','misconfigured','unknown')"),
        UniqueConstraint('firewall_id', 'profile_name')
    )

class UserIPMapping(Base):
    __tablename__ = 'user_ip_mappings'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    firewall_id = Column(UUID(as_uuid=True), ForeignKey('firewalls.id'), nullable=False)
    ip_address = Column(String(45), nullable=False)
    mapped_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, nullable=False, server_default='true')
    source = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (CheckConstraint("source IN ('captive_portal','vpn','agent','manual')"),)

class FirewallGroupMapping(Base):
    __tablename__ = 'firewall_group_mappings'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    firewall_id = Column(UUID(as_uuid=True), ForeignKey('firewalls.id'), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=False)
    ldap_server_id = Column(UUID(as_uuid=True), ForeignKey('ldap_servers.id'), nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(16), server_default='active')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("status IN ('active','stale','empty','error')"),
        UniqueConstraint('firewall_id', 'group_id')
    )

class AuthenticationEvent(Base):
    __tablename__ = 'authentication_events'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    firewall_id = Column(UUID(as_uuid=True), ForeignKey('firewalls.id'), nullable=False)
    username_raw = Column(String(128), nullable=False)
    source_ip = Column(String(45), nullable=True)
    result = Column(String(16), nullable=False)
    failure_reason = Column(String(64), nullable=True)
    auth_method = Column(String(32), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        CheckConstraint("result IN ('success','failure','timeout','unknown')"),
        CheckConstraint("failure_reason IN ('bad_password','account_locked','ldap_error','timeout','unknown') OR failure_reason IS NULL"),
        CheckConstraint("auth_method IN ('kerberos','ntlm','radius','local') OR auth_method IS NULL")
    )

class DiagnosticRun(Base):
    __tablename__ = 'diagnostic_runs'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    run_type = Column(String(16), nullable=False)
    subject_username = Column(String(64), nullable=True)
    subject_firewall_id = Column(UUID(as_uuid=True), ForeignKey('firewalls.id'), nullable=True)
    status = Column(String(16), nullable=False)
    overall_result = Column(String(32), nullable=False)
    overall_status = Column(String(16), nullable=False)
    results_json = Column(JSONB, nullable=False)
    triggered_by = Column(String(64), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        CheckConstraint("run_type IN ('user','firewall')"),
        CheckConstraint("status IN ('complete','error')"),
        CheckConstraint("overall_status IN ('HEALTHY','DEGRADED','FAILED')")
    )

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(32), nullable=True)
    resource_id = Column(Text, nullable=True)
    request_ip = Column(String(45), nullable=True)
    request_id = Column(String(36), nullable=True)
    extra = Column(JSONB, nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

# Indexes
Index('ix_users_username', User.username)
Index('ix_users_email', User.email)
Index('ix_ugm_user_id', UserGroupMembership.user_id)
Index('ix_ugm_group_id', UserGroupMembership.group_id)
Index('ix_fw_status', Firewall.status)
Index('ix_ldap_fw_id', LDAPServer.firewall_id)
Index('ix_ipm_ip', UserIPMapping.ip_address)
Index('ix_ipm_user_current', UserIPMapping.user_id, UserIPMapping.is_current)
Index('ix_fgm_fw_id', FirewallGroupMapping.firewall_id)
Index('ix_ae_user_time', AuthenticationEvent.user_id, AuthenticationEvent.occurred_at)
Index('ix_ae_fw_time', AuthenticationEvent.firewall_id, AuthenticationEvent.occurred_at)
Index('ix_ae_occurred', AuthenticationEvent.occurred_at)
Index('ix_dr_username', DiagnosticRun.subject_username)
Index('ix_al_occurred', AuditLog.occurred_at)

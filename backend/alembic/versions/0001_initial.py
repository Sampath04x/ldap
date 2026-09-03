"""Initial migration

Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('department', sa.String(length=128), nullable=True),
        sa.Column('job_title', sa.String(length=128), nullable=True),
        sa.Column('location', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='active', nullable=False),
        sa.Column('ldap_dn', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('active','inactive','disabled','locked')"),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=False)
    op.execute("CREATE INDEX ix_users_username_trgm ON users USING GIN (username gin_trgm_ops)")
    op.execute("CREATE INDEX ix_users_display_name_trgm ON users USING GIN (display_name gin_trgm_ops)")

    op.create_table('groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='active', nullable=True),
        sa.Column('ldap_dn', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('active','disabled')"),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_name')
    )
    op.execute("CREATE INDEX ix_groups_group_name_trgm ON groups USING GIN (group_name gin_trgm_ops)")

    op.create_table('user_group_memberships',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("source IN ('ldap','manual','sync')"),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'group_id')
    )
    op.create_index('ix_ugm_group_id', 'user_group_memberships', ['group_id'], unique=False)
    op.create_index('ix_ugm_user_id', 'user_group_memberships', ['user_id'], unique=False)

    op.create_table('firewalls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=False),
        sa.Column('model', sa.String(length=64), nullable=True),
        sa.Column('software_version', sa.String(length=32), nullable=True),
        sa.Column('environment', sa.String(length=32), server_default='production', nullable=True),
        sa.Column('location', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='unknown', nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("environment IN ('production','staging','lab')"),
        sa.CheckConstraint("status IN ('reachable','unreachable','degraded','unknown')"),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname')
    )
    op.create_index('ix_fw_status', 'firewalls', ['status'], unique=False)
    op.execute("CREATE INDEX ix_firewalls_hostname_trgm ON firewalls USING GIN (hostname gin_trgm_ops)")

    op.create_table('ldap_servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('firewall_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_name', sa.String(length=128), nullable=False),
        sa.Column('server_host', sa.String(length=255), nullable=False),
        sa.Column('server_port', sa.Integer(), server_default='389', nullable=True),
        sa.Column('use_tls', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('base_dn', sa.Text(), nullable=True),
        sa.Column('bind_dn', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='unknown', nullable=True),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("server_port >= 1 AND server_port <= 65535"),
        sa.CheckConstraint("status IN ('reachable','unreachable','tls_error','misconfigured','unknown')"),
        sa.ForeignKeyConstraint(['firewall_id'], ['firewalls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('firewall_id', 'profile_name')
    )
    op.create_index('ix_ldap_fw_id', 'ldap_servers', ['firewall_id'], unique=False)

    op.create_table('user_ip_mappings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('firewall_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=False),
        sa.Column('mapped_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('source', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("source IN ('captive_portal','vpn','agent','manual')"),
        sa.ForeignKeyConstraint(['firewall_id'], ['firewalls.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ipm_ip', 'user_ip_mappings', ['ip_address'], unique=False)
    op.create_index('ix_ipm_user_current', 'user_ip_mappings', ['user_id', 'is_current'], unique=False)
    op.execute("CREATE UNIQUE INDEX ix_ipm_current_unique ON user_ip_mappings (user_id, firewall_id, ip_address) WHERE is_current = true")

    op.create_table('firewall_group_mappings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('firewall_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ldap_server_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='active', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('active','stale','empty','error')"),
        sa.ForeignKeyConstraint(['firewall_id'], ['firewalls.id'], ),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.ForeignKeyConstraint(['ldap_server_id'], ['ldap_servers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('firewall_id', 'group_id')
    )
    op.create_index('ix_fgm_fw_id', 'firewall_group_mappings', ['firewall_id'], unique=False)

    op.create_table('authentication_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('firewall_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username_raw', sa.String(length=128), nullable=False),
        sa.Column('source_ip', postgresql.INET(), nullable=True),
        sa.Column('result', sa.String(length=16), nullable=False),
        sa.Column('failure_reason', sa.String(length=64), nullable=True),
        sa.Column('auth_method', sa.String(length=32), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("auth_method IN ('kerberos','ntlm','radius','local') OR auth_method IS NULL"),
        sa.CheckConstraint("failure_reason IN ('bad_password','account_locked','ldap_error','timeout','unknown') OR failure_reason IS NULL"),
        sa.CheckConstraint("result IN ('success','failure','timeout','unknown')"),
        sa.ForeignKeyConstraint(['firewall_id'], ['firewalls.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ae_fw_time', 'authentication_events', ['firewall_id', 'occurred_at'], unique=False)
    op.create_index('ix_ae_occurred', 'authentication_events', ['occurred_at'], unique=False)
    op.create_index('ix_ae_user_time', 'authentication_events', ['user_id', 'occurred_at'], unique=False)

    op.create_table('diagnostic_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('run_type', sa.String(length=16), nullable=False),
        sa.Column('subject_username', sa.String(length=64), nullable=True),
        sa.Column('subject_firewall_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('overall_result', sa.String(length=32), nullable=False),
        sa.Column('overall_status', sa.String(length=16), nullable=False),
        sa.Column('results_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('triggered_by', sa.String(length=64), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("overall_status IN ('HEALTHY','DEGRADED','FAILED')"),
        sa.CheckConstraint("run_type IN ('user','firewall')"),
        sa.CheckConstraint("status IN ('complete','error')"),
        sa.ForeignKeyConstraint(['subject_firewall_id'], ['firewalls.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dr_username', 'diagnostic_runs', ['subject_username'], unique=False)

    op.create_table('audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('actor', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=32), nullable=True),
        sa.Column('resource_id', sa.Text(), nullable=True),
        sa.Column('request_ip', postgresql.INET(), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_al_occurred', 'audit_logs', ['occurred_at'], unique=False)

def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('diagnostic_runs')
    op.drop_table('authentication_events')
    op.drop_table('firewall_group_mappings')
    op.drop_table('user_ip_mappings')
    op.drop_table('ldap_servers')
    op.drop_table('firewalls')
    op.drop_table('user_group_memberships')
    op.drop_table('groups')
    op.drop_table('users')
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")

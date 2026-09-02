from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import List

from app.providers.base import (
    PaloAltoProvider, FirewallStatus, UserIdentity, IPMapping, 
    LDAPConfig, LDAPConnResult, GroupMappingState
)
from app.models import (
    Firewall, User, UserIPMapping, LDAPServer, 
    UserGroupMembership, Group, FirewallGroupMapping
)

class MockPaloAltoProvider(PaloAltoProvider):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_firewall_status(self, firewall_id: str) -> FirewallStatus:
        result = await self.session.execute(select(Firewall).where(Firewall.id == firewall_id))
        fw = result.scalar_one_or_none()
        if not fw:
            return FirewallStatus(reachable=False, status='unknown', last_seen_at=None, detail="Firewall not found")
        reachable = fw.status == 'reachable'
        return FirewallStatus(
            reachable=reachable,
            status=fw.status,
            last_seen_at=fw.last_seen_at,
            detail=f"Status: {fw.status}"
        )

    async def get_user_identity(self, username: str, firewall_id: str) -> UserIdentity:
        result = await self.session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            return UserIdentity(found=False, username=username, status='unknown', display_name='', ldap_dn=None, detail="User not found")
        return UserIdentity(
            found=True,
            username=user.username,
            status=user.status,
            display_name=user.display_name,
            ldap_dn=user.ldap_dn,
            detail="User found in database"
        )

    async def get_user_ip_mappings(self, username: str, firewall_id: str) -> list[IPMapping]:
        result = await self.session.execute(
            select(UserIPMapping)
            .join(User)
            .where(User.username == username, UserIPMapping.firewall_id == firewall_id)
        )
        mappings = result.scalars().all()
        now = datetime.now(timezone.utc)
        return [
            IPMapping(
                ip_address=m.ip_address,
                mapped_at=m.mapped_at,
                is_current=m.is_current,
                source=m.source,
                age_hours=(now - m.mapped_at).total_seconds() / 3600
            ) for m in mappings
        ]

    async def get_ldap_configs(self, firewall_id: str) -> list[LDAPConfig]:
        result = await self.session.execute(select(LDAPServer).where(LDAPServer.firewall_id == firewall_id))
        servers = result.scalars().all()
        return [
            LDAPConfig(
                profile_name=s.profile_name,
                server_host=s.server_host,
                server_port=s.server_port,
                use_tls=s.use_tls,
                base_dn=s.base_dn,
                bind_dn=s.bind_dn
            ) for s in servers
        ]

    async def test_ldap_connectivity(self, firewall_id: str, profile: str) -> LDAPConnResult:
        result = await self.session.execute(
            select(LDAPServer).where(LDAPServer.firewall_id == firewall_id, LDAPServer.profile_name == profile)
        )
        server = result.scalar_one_or_none()
        if not server:
            return LDAPConnResult(reachable=False, status='unknown', detail="LDAP profile not found")
        reachable = server.status == 'reachable'
        return LDAPConnResult(
            reachable=reachable,
            status=server.status,
            detail=f"LDAP status: {server.status}"
        )

    async def get_user_groups(self, username: str, firewall_id: str) -> list[str]:
        result = await self.session.execute(
            select(Group.group_name)
            .join(UserGroupMembership)
            .join(User)
            .where(User.username == username, Group.status == 'active')
        )
        return list(result.scalars().all())

    async def get_group_mapping_state(self, firewall_id: str) -> GroupMappingState:
        result = await self.session.execute(
            select(FirewallGroupMapping, Group.group_name)
            .join(Group, FirewallGroupMapping.group_id == Group.id)
            .where(FirewallGroupMapping.firewall_id == firewall_id)
        )
        rows = result.all()
        if not rows:
            return GroupMappingState(mapped_groups=[], last_synced_at=None, age_hours=None, status='empty')

        group_names = [row[1] for row in rows]
        mappings = [row[0] for row in rows]
        latest_sync = max((m.synced_at for m in mappings if m.synced_at), default=None)

        age = None
        if latest_sync:
            age = (datetime.now(timezone.utc) - latest_sync).total_seconds() / 3600

        statuses = set(m.status for m in mappings)
        if 'error' in statuses:
            status = 'error'
        elif 'stale' in statuses:
            status = 'stale'
        elif not group_names:
            status = 'empty'
        else:
            status = 'active'

        return GroupMappingState(
            mapped_groups=group_names,
            last_synced_at=latest_sync,
            age_hours=age,
            status=status
        )

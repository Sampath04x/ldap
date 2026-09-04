import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.services.diagnostics import DiagnosticEngine, DiagnosticCode
from app.providers.mock import MockPaloAltoProvider
from app.config import get_settings
from app.models import (
    User, Firewall, LDAPServer, UserIPMapping, Group, 
    UserGroupMembership, FirewallGroupMapping, AuthenticationEvent
)

@pytest.mark.asyncio
async def test_user_not_found_vs_not_identified(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-idtest.corp", ip_address="10.0.0.1", status="reachable")
    user = User(id=uuid.UUID(user_id), username="existing_dir_user", email="existing@corp.com", display_name="Existing User", status="active")
    test_db.add_all([fw, user])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())

    # 1. Non-existent user -> USER_NOT_FOUND
    res1 = await engine.run_user_diagnostic(fw_id, "nonexistent_user", "tester")
    check_id1 = next(c for c in res1.checks if c.name == "User Identity")
    assert check_id1.code == DiagnosticCode.USER_NOT_FOUND.value

    # 2. Directory user exists, but no User-ID session on target firewall -> USER_NOT_IDENTIFIED
    res2 = await engine.run_user_diagnostic(fw_id, "existing_dir_user", "tester")
    check_id2 = next(c for c in res2.checks if c.name == "User Identity")
    assert check_id2.code == DiagnosticCode.USER_NOT_IDENTIFIED.value


@pytest.mark.asyncio
async def test_user_account_status_states(test_db):
    fw_id = str(uuid.uuid4())
    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-statustest.corp", ip_address="10.0.0.2", status="reachable")
    test_db.add(fw)

    # Add active session mapping for each test user
    statuses = ["disabled", "locked", "inactive", "active"]
    for idx, st in enumerate(statuses):
        u_id = str(uuid.uuid4())
        uname = f"user_{st}"
        u = User(id=uuid.UUID(u_id), username=uname, email=f"{uname}@corp.com", display_name=f"User {st}", status=st)
        ipm = UserIPMapping(user_id=uuid.UUID(u_id), firewall_id=uuid.UUID(fw_id), ip_address=f"10.1.1.{10+idx}", mapped_at=datetime.now(timezone.utc), is_current=True)
        test_db.add_all([u, ipm])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())

    for st in ["disabled", "locked", "inactive"]:
        res = await engine.run_user_diagnostic(fw_id, f"user_{st}", "tester")
        check_id = next(c for c in res.checks if c.name == "User Identity")
        assert check_id.code == DiagnosticCode.USER_INACTIVE.value

    res_active = await engine.run_user_diagnostic(fw_id, "user_active", "tester")
    check_active = next(c for c in res_active.checks if c.name == "User Identity")
    assert check_active.passed is True


@pytest.mark.asyncio
async def test_group_mapping_edge_cases(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    ldap_id = str(uuid.uuid4())
    g1_id = str(uuid.uuid4())
    g2_id = str(uuid.uuid4())

    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-grouptest.corp", ip_address="10.0.0.3", status="reachable")
    user = User(id=uuid.UUID(user_id), username="grp_edge_user", email="grp_edge@corp.com", display_name="Grp Edge User", status="active")
    ldap = LDAPServer(id=uuid.UUID(ldap_id), firewall_id=uuid.UUID(fw_id), profile_name="main_ldap", server_host="10.0.0.250", status="reachable")
    ipm = UserIPMapping(user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.20", mapped_at=datetime.now(timezone.utc), is_current=True)

    g1 = Group(id=uuid.UUID(g1_id), group_name="GRP-ALLOW-NET", display_name="Net Allow", status="active")
    g2 = Group(id=uuid.UUID(g2_id), group_name="GRP-DENY-WEB", display_name="Web Deny", status="active")
    m1 = UserGroupMembership(user_id=uuid.UUID(user_id), group_id=uuid.UUID(g1_id), source="ldap")
    m2 = UserGroupMembership(user_id=uuid.UUID(user_id), group_id=uuid.UUID(g2_id), source="ldap")

    # Only map g1 on firewall initially (g2 missing)
    fgm1 = FirewallGroupMapping(firewall_id=uuid.UUID(fw_id), group_id=uuid.UUID(g1_id), ldap_server_id=uuid.UUID(ldap_id), status="active", synced_at=datetime.now(timezone.utc))

    test_db.add_all([fw, user, ldap, ipm, g1, g2, m1, m2, fgm1])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())

    # 1. One user group missing on firewall -> WARNING (GROUP_MAPPING_EMPTY code)
    res1 = await engine.run_user_diagnostic(fw_id, "grp_edge_user", "tester")
    check_grp1 = next(c for c in res1.checks if c.name == "Group Membership")
    assert check_grp1.passed is False
    assert "missing" in check_grp1.detail.lower()

    # 2. Add g2 mapping -> PASSED
    fgm2 = FirewallGroupMapping(firewall_id=uuid.UUID(fw_id), group_id=uuid.UUID(g2_id), ldap_server_id=uuid.UUID(ldap_id), status="active", synced_at=datetime.now(timezone.utc))
    test_db.add(fgm2)
    await test_db.commit()

    res2 = await engine.run_user_diagnostic(fw_id, "grp_edge_user", "tester")
    check_grp2 = next(c for c in res2.checks if c.name == "Group Membership")
    assert check_grp2.passed is True


@pytest.mark.asyncio
async def test_ip_mapping_edge_cases(test_db):
    fw_id = str(uuid.uuid4())
    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-iptest.corp", ip_address="10.0.0.4", status="reachable")
    test_db.add(fw)

    # 1. Expired mapping
    u1_id = str(uuid.uuid4())
    u1 = User(id=uuid.UUID(u1_id), username="expired_ip_user", email="exp@corp.com", display_name="Expired User", status="active")
    ipm1 = UserIPMapping(
        user_id=uuid.UUID(u1_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.30", 
        mapped_at=datetime.now(timezone.utc) - timedelta(hours=24), 
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1), is_current=False
    )
    test_db.add_all([u1, ipm1])

    # 2. IPv6 current mapping
    u2_id = str(uuid.uuid4())
    u2 = User(id=uuid.UUID(u2_id), username="ipv6_user", email="v6@corp.com", display_name="IPv6 User", status="active")
    ipm2 = UserIPMapping(
        user_id=uuid.UUID(u2_id), firewall_id=uuid.UUID(fw_id), ip_address="2001:db8::1", 
        mapped_at=datetime.now(timezone.utc), is_current=True
    )
    test_db.add_all([u2, ipm2])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())

    res_exp = await engine.run_user_diagnostic(fw_id, "expired_ip_user", "tester")
    check_ip_exp = next(c for c in res_exp.checks if c.name == "IP Mapping")
    assert check_ip_exp.passed is False

    res_v6 = await engine.run_user_diagnostic(fw_id, "ipv6_user", "tester")
    check_ip_v6 = next(c for c in res_v6.checks if c.name == "IP Mapping")
    assert check_ip_v6.passed is True


@pytest.mark.asyncio
async def test_auth_history_threshold_edge_cases(test_db):
    fw_id = str(uuid.uuid4())
    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-authedge.corp", ip_address="10.0.0.5", status="reachable")
    test_db.add(fw)

    # User A: Exactly threshold (3 failures)
    ua_id = str(uuid.uuid4())
    ua = User(id=uuid.UUID(ua_id), username="user_3fails", email="3f@corp.com", display_name="3 Fails User", status="active")
    ipma = UserIPMapping(user_id=uuid.UUID(ua_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.40", mapped_at=datetime.now(timezone.utc), is_current=True)
    events_a = [
        AuthenticationEvent(
            user_id=uuid.UUID(ua_id), firewall_id=uuid.UUID(fw_id), username_raw="user_3fails",
            result="failure", failure_reason="bad_password", occurred_at=datetime.now(timezone.utc) - timedelta(minutes=5 * i)
        ) for i in range(3)
    ]
    test_db.add_all([ua, ipma] + events_a)

    # User B: Threshold - 1 (2 failures)
    ub_id = str(uuid.uuid4())
    ub = User(id=uuid.UUID(ub_id), username="user_2fails", email="2f@corp.com", display_name="2 Fails User", status="active")
    ipmb = UserIPMapping(user_id=uuid.UUID(ub_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.41", mapped_at=datetime.now(timezone.utc), is_current=True)
    events_b = [
        AuthenticationEvent(
            user_id=uuid.UUID(ub_id), firewall_id=uuid.UUID(fw_id), username_raw="user_2fails",
            result="failure", failure_reason="bad_password", occurred_at=datetime.now(timezone.utc) - timedelta(minutes=5 * i)
        ) for i in range(2)
    ]
    test_db.add_all([ub, ipmb] + events_b)
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())

    res_a = await engine.run_user_diagnostic(fw_id, "user_3fails", "tester")
    check_auth_a = next(c for c in res_a.checks if c.name == "Authentication History")
    assert check_auth_a.passed is False
    assert check_auth_a.code == DiagnosticCode.AUTHENTICATION_FAILURE.value

    res_b = await engine.run_user_diagnostic(fw_id, "user_2fails", "tester")
    check_auth_b = next(c for c in res_b.checks if c.name == "Authentication History")
    assert check_auth_b.passed is True

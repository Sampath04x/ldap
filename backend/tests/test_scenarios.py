import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.models import User, Firewall, LDAPServer, UserIPMapping, FirewallGroupMapping, Group, UserGroupMembership, AuthenticationEvent
from app.services.diagnostics import DiagnosticEngine
from app.providers.mock import MockPaloAltoProvider
from app.config import get_settings

@pytest.mark.asyncio
async def test_scenario_healthy_user(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    group_id = str(uuid.uuid4())
    ldap_id = str(uuid.uuid4())
    username = "alice_healthy"

    # Seed healthy topology
    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-healthy.corp", ip_address="10.0.0.1", status="reachable")
    user = User(id=uuid.UUID(user_id), username=username, email=f"{username}@corp.com", display_name="Alice Healthy", status="active")
    grp = Group(id=uuid.UUID(group_id), group_name="GRP-NETOPS", status="active")
    ugm = UserGroupMembership(user_id=uuid.UUID(user_id), group_id=uuid.UUID(group_id), source="ldap")
    ldap = LDAPServer(id=uuid.UUID(ldap_id), firewall_id=uuid.UUID(fw_id), profile_name="default", server_host="10.0.0.250", status="reachable")
    ipm = UserIPMapping(user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.50", mapped_at=datetime.now(timezone.utc), is_current=True)
    fgm = FirewallGroupMapping(firewall_id=uuid.UUID(fw_id), group_id=uuid.UUID(group_id), status="active", synced_at=datetime.now(timezone.utc))

    test_db.add_all([fw, user, grp, ugm, ldap, ipm, fgm])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, username, "test_harness")

    assert res.overall_status == "HEALTHY"
    assert res.overall_result == "IDENTITY_HEALTHY"
    assert all(c.passed for c in res.checks)

@pytest.mark.asyncio
async def test_scenario_unreachable_firewall(test_db):
    fw_id = str(uuid.uuid4())
    username = "bob_unreachable"

    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-down.corp", ip_address="10.0.0.2", status="unreachable")
    test_db.add(fw)
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, username, "test_harness")

    assert res.overall_status == "FAILED"
    assert res.overall_result == "FIREWALL_UNREACHABLE"
    assert len(res.checks) == 1  # Stop-chain stopped after firewall reachability check

@pytest.mark.asyncio
async def test_scenario_missing_ldap_config(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    username = "charlie_noldap"

    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-no-ldap.corp", ip_address="10.0.0.3", status="reachable")
    user = User(id=uuid.UUID(user_id), username=username, email=f"{username}@corp.com", display_name="Charlie NoLDAP", status="active")
    ipm = UserIPMapping(user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.51", mapped_at=datetime.now(timezone.utc), is_current=True)

    test_db.add_all([fw, user, ipm])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, username, "test_harness")

    assert res.overall_status == "DEGRADED"
    assert any(c.code == "LDAP_NOT_CONFIGURED" for c in res.checks)
    # Downstream LDAP checks marked as skipped
    skipped_checks = [c for c in res.checks if c.code == "SKIPPED"]
    assert len(skipped_checks) == 3

@pytest.mark.asyncio
async def test_scenario_user_not_found(test_db):
    fw_id = str(uuid.uuid4())
    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-nf.corp", ip_address="10.0.0.5", status="reachable")
    test_db.add(fw)
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, "ghost_user", "test_harness")

    assert res.overall_status == "FAILED"
    assert any(c.code == "USER_NOT_FOUND" for c in res.checks)

@pytest.mark.asyncio
async def test_scenario_user_not_identified(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    username = "locked_user"

    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-lock.corp", ip_address="10.0.0.6", status="reachable")
    user = User(id=uuid.UUID(user_id), username=username, email=f"{username}@corp.com", display_name="Locked User", status="disabled")
    test_db.add_all([fw, user])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, username, "test_harness")

    assert res.overall_status == "FAILED"
    assert any(c.code == "USER_NOT_IDENTIFIED" for c in res.checks)

@pytest.mark.asyncio
async def test_scenario_missing_ip_mapping(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    username = "noip_user"

    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-noip.corp", ip_address="10.0.0.7", status="reachable")
    user = User(id=uuid.UUID(user_id), username=username, email=f"{username}@corp.com", display_name="No IP User", status="active")
    test_db.add_all([fw, user])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, username, "test_harness")

    assert res.overall_status == "DEGRADED"
    assert any(c.code == "IP_MAPPING_MISSING" for c in res.checks)

@pytest.mark.asyncio
async def test_scenario_ldap_unreachable(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    ldap_id = str(uuid.uuid4())
    username = "ldap_down_user"

    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-ldapdown.corp", ip_address="10.0.0.8", status="reachable")
    user = User(id=uuid.UUID(user_id), username=username, email=f"{username}@corp.com", display_name="LDAP Down User", status="active")
    ldap = LDAPServer(id=uuid.UUID(ldap_id), firewall_id=uuid.UUID(fw_id), profile_name="primary", server_host="10.0.0.251", status="unreachable")
    ipm = UserIPMapping(user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.53", mapped_at=datetime.now(timezone.utc), is_current=True)

    test_db.add_all([fw, user, ldap, ipm])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, username, "test_harness")

    assert res.overall_status == "FAILED"
    assert any(c.code == "LDAP_UNREACHABLE" for c in res.checks)

@pytest.mark.asyncio
async def test_scenario_ldap_tls_failure(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    ldap_id = str(uuid.uuid4())
    username = "tls_fail_user"

    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-tlserr.corp", ip_address="10.0.0.9", status="reachable")
    user = User(id=uuid.UUID(user_id), username=username, email=f"{username}@corp.com", display_name="TLS Fail User", status="active")
    ldap = LDAPServer(id=uuid.UUID(ldap_id), firewall_id=uuid.UUID(fw_id), profile_name="secure_ldap", server_host="10.0.0.252", status="tls_error")
    ipm = UserIPMapping(user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.54", mapped_at=datetime.now(timezone.utc), is_current=True)

    test_db.add_all([fw, user, ldap, ipm])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, username, "test_harness")

    assert res.overall_status == "FAILED"
    assert any(c.code == "LDAP_TLS_FAILURE" for c in res.checks)

@pytest.mark.asyncio
async def test_scenario_no_groups(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    ldap_id = str(uuid.uuid4())
    username = "nogroups_user"

    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-nogrp.corp", ip_address="10.0.0.10", status="reachable")
    user = User(id=uuid.UUID(user_id), username=username, email=f"{username}@corp.com", display_name="No Groups User", status="active")
    ldap = LDAPServer(id=uuid.UUID(ldap_id), firewall_id=uuid.UUID(fw_id), profile_name="default", server_host="10.0.0.250", status="reachable")
    ipm = UserIPMapping(user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.55", mapped_at=datetime.now(timezone.utc), is_current=True)

    test_db.add_all([fw, user, ldap, ipm])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, username, "test_harness")

    assert res.overall_status == "DEGRADED"
    assert any(c.code == "GROUP_MAPPING_EMPTY" for c in res.checks)

@pytest.mark.asyncio
async def test_scenario_authentication_failures(test_db):
    fw_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    username = "auth_fail_user"

    fw = Firewall(id=uuid.UUID(fw_id), hostname="fw-authfail.corp", ip_address="10.0.0.11", status="reachable")
    user = User(id=uuid.UUID(user_id), username=username, email=f"{username}@corp.com", display_name="Auth Fail User", status="active")
    ldap_id = str(uuid.uuid4())
    ldap = LDAPServer(id=uuid.UUID(ldap_id), firewall_id=uuid.UUID(fw_id), profile_name="default", server_host="10.0.0.250", status="reachable")
    ipm = UserIPMapping(user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw_id), ip_address="10.1.1.56", mapped_at=datetime.now(timezone.utc), is_current=True)

    # 4 auth failure events in past hour
    events = [
        AuthenticationEvent(
            user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw_id),
            username_raw=username, result="failure", failure_reason="bad_password",
            occurred_at=datetime.now(timezone.utc) - timedelta(minutes=10 * i)
        ) for i in range(4)
    ]

    test_db.add_all([fw, user, ldap, ipm] + events)
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw_id, username, "test_harness")

    assert res.overall_status == "DEGRADED"
    assert any(c.code == "AUTHENTICATION_FAILURE" for c in res.checks)

@pytest.mark.asyncio
async def test_scenario_inconsistent_identity(test_db):
    fw1_id = str(uuid.uuid4())
    fw2_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    username = "inconsistent_user"

    fw1 = Firewall(id=uuid.UUID(fw1_id), hostname="fw-loc1.corp", ip_address="10.0.0.12", status="reachable")
    fw2 = Firewall(id=uuid.UUID(fw2_id), hostname="fw-loc2.corp", ip_address="10.0.0.13", status="reachable")
    user = User(id=uuid.UUID(user_id), username=username, email=f"{username}@corp.com", display_name="Inconsistent User", status="active")
    ldap = LDAPServer(id=uuid.UUID(str(uuid.uuid4())), firewall_id=uuid.UUID(fw1_id), profile_name="default", server_host="10.0.0.250", status="reachable")

    # Conflicting current IP mappings for same user across two firewalls
    ipm1 = UserIPMapping(user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw1_id), ip_address="10.1.1.100", mapped_at=datetime.now(timezone.utc), is_current=True)
    ipm2 = UserIPMapping(user_id=uuid.UUID(user_id), firewall_id=uuid.UUID(fw2_id), ip_address="10.2.2.200", mapped_at=datetime.now(timezone.utc), is_current=True)

    test_db.add_all([fw1, fw2, user, ldap, ipm1, ipm2])
    await test_db.commit()

    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    res = await engine.run_user_diagnostic(fw1_id, username, "test_harness")

    assert res.overall_status == "DEGRADED"
    assert any(c.code == "IDENTITY_INCONSISTENT" for c in res.checks)

from enum import Enum
from typing import Optional
from datetime import datetime, timezone
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.providers.base import PaloAltoProvider, LDAPConfig
from app.config import Settings
from app.models import DiagnosticRun, Firewall, AuditLog, AuthenticationEvent, User
from app.schemas import DiagnosticRunResponse, DiagnosticCheck

class DiagnosticCode(str, Enum):
    OK = "OK"
    IDENTITY_HEALTHY = "IDENTITY_HEALTHY"
    FIREWALL_UNREACHABLE = "FIREWALL_UNREACHABLE"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_NOT_IDENTIFIED = "USER_NOT_IDENTIFIED"
    USER_INACTIVE = "USER_INACTIVE"
    IP_MAPPING_MISSING = "IP_MAPPING_MISSING"
    IDENTITY_MAPPING_STALE = "IDENTITY_MAPPING_STALE"
    LDAP_NOT_CONFIGURED = "LDAP_NOT_CONFIGURED"
    LDAP_UNREACHABLE = "LDAP_UNREACHABLE"
    LDAP_TLS_FAILURE = "LDAP_TLS_FAILURE"
    GROUP_MAPPING_EMPTY = "GROUP_MAPPING_EMPTY"
    GROUP_MAPPING_STALE = "GROUP_MAPPING_STALE"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    IDENTITY_INCONSISTENT = "IDENTITY_INCONSISTENT"
    SKIPPED = "SKIPPED"

class DiagnosticEngine:
    def __init__(self, provider: PaloAltoProvider, db: AsyncSession, settings: Settings):
        self.provider = provider
        self.db = db
        self.settings = settings

    async def run_user_diagnostic(self, firewall_id: str, username: str, triggered_by: str) -> DiagnosticRunResponse:
        start_time = time.time()
        checks: list[DiagnosticCheck] = []
        
        # 1. Firewall Reachability
        check_fw = await self._check_firewall_reachability(firewall_id)
        checks.append(check_fw)
        if not check_fw.passed:
            return await self._finalize_run(firewall_id, username, triggered_by, start_time, checks, check_fw.code)
            
        # 2. User Identity
        check_id = await self._check_user_identity(username, firewall_id)
        checks.append(check_id)
        if not check_id.passed:
            pass # Continue to get more context
            
        # 3. IP Mapping
        check_ip = await self._check_ip_mapping(username, firewall_id)
        checks.append(check_ip)
        
        # 4. LDAP Config
        check_ldap_conf, ldap_configs = await self._check_ldap_config(firewall_id)
        checks.append(check_ldap_conf)
        
        if not check_ldap_conf.passed:
            # Skip 5, 6, 7
            checks.extend([
                DiagnosticCheck(name="LDAP Connectivity", passed=False, code=DiagnosticCode.SKIPPED.value, severity="info", detail="Skipped due to missing LDAP config"),
                DiagnosticCheck(name="Group Membership", passed=False, code=DiagnosticCode.SKIPPED.value, severity="info", detail="Skipped due to missing LDAP config"),
                DiagnosticCheck(name="Group Mapping Freshness", passed=False, code=DiagnosticCode.SKIPPED.value, severity="info", detail="Skipped due to missing LDAP config")
            ])
            user_groups = []
        else:
            # 5. LDAP Connectivity
            check_ldap_conn = await self._check_ldap_connectivity(firewall_id, ldap_configs)
            checks.append(check_ldap_conn)
            
            # 6. Group Membership
            check_group, user_groups = await self._check_group_membership(username, firewall_id)
            checks.append(check_group)
            
            # 7. Group Mapping Freshness
            check_group_map = await self._check_group_mapping_freshness(firewall_id)
            checks.append(check_group_map)

        # 8. Auth History
        check_auth = await self._check_auth_history(username, firewall_id)
        checks.append(check_auth)
        
        # 9. Identity Consistency
        check_cons = await self._check_identity_consistency(username, firewall_id)
        checks.append(check_cons)

        return await self._finalize_run(firewall_id, username, triggered_by, start_time, checks)

    async def _finalize_run(self, fw_id: str, username: str, triggered_by: str, start_time: float, checks: list[DiagnosticCheck], override_code: str = None) -> DiagnosticRunResponse:
        duration_ms = int((time.time() - start_time) * 1000)
        
        if override_code:
            overall_result = override_code
            overall_status = "FAILED"
        else:
            has_critical = any(not c.passed and c.severity == "critical" for c in checks if c.code != DiagnosticCode.SKIPPED.value)
            has_high_med = any(not c.passed and c.severity in ("high", "medium") for c in checks if c.code != DiagnosticCode.SKIPPED.value)
            
            if has_critical:
                overall_status = "FAILED"
                failed_checks = [c for c in checks if not c.passed and c.severity == "critical"]
                overall_result = failed_checks[0].code if failed_checks else "FAILED"
            elif has_high_med:
                overall_status = "DEGRADED"
                degraded_checks = [c for c in checks if not c.passed and c.severity in ("high", "medium")]
                overall_result = degraded_checks[0].code if degraded_checks else "DEGRADED"
            else:
                overall_status = "HEALTHY"
                overall_result = DiagnosticCode.IDENTITY_HEALTHY.value

        summary = f"Diagnostic run completed with status {overall_status}."

        result = await self.db.execute(select(Firewall).where(Firewall.id == fw_id))
        fw = result.scalar_one_or_none()
        fw_name = fw.hostname if fw else str(fw_id)
        
        run = DiagnosticRun(
            run_type="user",
            subject_username=username,
            subject_firewall_id=fw_id,
            status="complete",
            overall_result=overall_result,
            overall_status=overall_status,
            results_json=[c.model_dump() for c in checks],
            triggered_by=triggered_by,
            duration_ms=duration_ms
        )
        self.db.add(run)
        
        audit = AuditLog(
            actor=triggered_by,
            action="run_diagnostic",
            resource_type="diagnostic_run",
            extra={"username": username, "firewall_id": str(fw_id), "status": overall_status}
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(run)
        
        return DiagnosticRunResponse(
            run_id=run.id,
            subject=username,
            firewall=fw_name,
            overall_result=overall_result,
            overall_status=overall_status,
            duration_ms=duration_ms,
            checks=checks,
            summary=summary,
            created_at=run.created_at
        )

    async def _check_firewall_reachability(self, firewall_id: str) -> DiagnosticCheck:
        status = await self.provider.get_firewall_status(firewall_id)
        if not status.reachable:
            return DiagnosticCheck(
                name="Firewall Reachability", passed=False, status="FAILED",
                code=DiagnosticCode.FIREWALL_UNREACHABLE.value, severity="critical",
                detail=status.detail, evidence=f"Firewall status: {status.status}, last seen: {status.last_seen_at}",
                action="Verify physical network connectivity, management IP, and firewall power."
            )
        return DiagnosticCheck(
            name="Firewall Reachability", passed=True, status="PASSED",
            code=DiagnosticCode.OK.value, severity="info",
            detail="Firewall is reachable.", evidence=f"Firewall status: {status.status}", action=None
        )

    async def _check_user_identity(self, username: str, firewall_id: str) -> DiagnosticCheck:
        ident = await self.provider.get_user_identity(username, firewall_id)
        if not ident.found:
            return DiagnosticCheck(
                name="User Identity", passed=False, status="FAILED",
                code=DiagnosticCode.USER_NOT_FOUND.value, severity="critical",
                detail=f"User '{username}' not found in firewall identity store.",
                evidence=f"Queried identity store for user '{username}'", action="Verify username spelling or check identity agent mapping."
            )
        if ident.status == "disabled" or ident.status == "locked":
            return DiagnosticCheck(
                name="User Identity", passed=False, status="FAILED",
                code=DiagnosticCode.USER_NOT_IDENTIFIED.value, severity="high",
                detail=f"User '{username}' is present but status is {ident.status}.",
                evidence=f"Account status: {ident.status}, DN: {ident.ldap_dn}", action="Unlock or enable user account in Active Directory."
            )
        if ident.status != "active":
            return DiagnosticCheck(
                name="User Identity", passed=False, status="WARNING",
                code=DiagnosticCode.USER_INACTIVE.value, severity="high",
                detail=f"User '{username}' account status is {ident.status}.",
                evidence=f"Account status: {ident.status}", action="Check account state in Directory Services."
            )
        return DiagnosticCheck(
            name="User Identity", passed=True, status="PASSED",
            code=DiagnosticCode.OK.value, severity="info",
            detail=f"User '{username}' found and active.",
            evidence=f"DN: {ident.ldap_dn}", action=None
        )

    async def _check_ip_mapping(self, username: str, firewall_id: str) -> DiagnosticCheck:
        mappings = await self.provider.get_user_ip_mappings(username, firewall_id)
        if not mappings:
            return DiagnosticCheck(
                name="IP Mapping", passed=False, status="FAILED",
                code=DiagnosticCode.IP_MAPPING_MISSING.value, severity="high",
                detail="No IP address mappings found for user on firewall.",
                evidence="0 IP mapping records found", action="Verify GlobalProtect connection or Captive Portal login."
            )
        
        current_mappings = [m for m in mappings if m.is_current]
        if not current_mappings:
            return DiagnosticCheck(
                name="IP Mapping", passed=False, status="WARNING",
                code=DiagnosticCode.IDENTITY_MAPPING_STALE.value, severity="medium",
                detail="No current active IP mapping found.",
                evidence=f"Total historical mappings: {len(mappings)}, active: 0", action="User may need to re-authenticate."
            )
            
        stale = any(m.age_hours > self.settings.ip_mapping_stale_hours for m in current_mappings)
        if stale:
            max_age = max(m.age_hours for m in current_mappings)
            return DiagnosticCheck(
                name="IP Mapping", passed=False, status="WARNING",
                code=DiagnosticCode.IDENTITY_MAPPING_STALE.value, severity="medium",
                detail=f"Current IP mapping is stale ({max_age:.1f} hours old).",
                evidence=f"Current IP: {current_mappings[0].ip_address}, mapped {max_age:.1f}h ago", action="Verify User-ID timeout configurations."
            )
            
        return DiagnosticCheck(
            name="IP Mapping", passed=True, status="PASSED",
            code=DiagnosticCode.OK.value, severity="info",
            detail=f"Found {len(current_mappings)} current IP mapping(s).",
            evidence=f"Active IP: {current_mappings[0].ip_address}", action=None
        )

    async def _check_ldap_config(self, firewall_id: str) -> tuple[DiagnosticCheck, list[LDAPConfig]]:
        configs = await self.provider.get_ldap_configs(firewall_id)
        if not configs:
            return DiagnosticCheck(
                name="LDAP Configuration", passed=False, status="FAILED",
                code=DiagnosticCode.LDAP_NOT_CONFIGURED.value, severity="high",
                detail="No LDAP profiles configured on firewall.",
                evidence="0 LDAP server profiles found", action="Configure LDAP Server Profile on PAN-OS."
            ), configs
        return DiagnosticCheck(
            name="LDAP Configuration", passed=True, status="PASSED",
            code=DiagnosticCode.OK.value, severity="info",
            detail=f"Found {len(configs)} LDAP profile(s).",
            evidence=f"Profiles: {[c.profile_name for c in configs]}", action=None
        ), configs

    async def _check_ldap_connectivity(self, firewall_id: str, configs: list[LDAPConfig]) -> DiagnosticCheck:
        for config in configs:
            res = await self.provider.test_ldap_connectivity(firewall_id, config.profile_name)
            if not res.reachable:
                code = DiagnosticCode.LDAP_TLS_FAILURE.value if res.status == 'tls_error' else DiagnosticCode.LDAP_UNREACHABLE.value
                return DiagnosticCheck(
                    name="LDAP Connectivity", passed=False, status="FAILED",
                    code=code, severity="critical",
                    detail=f"Profile {config.profile_name} failed: {res.detail}",
                    evidence=f"Host: {config.server_host}:{config.server_port}, TLS: {config.use_tls}, status: {res.status}",
                    action="Check LDAP service port routing, firewall security rules, and TLS certificate validity."
                )
        return DiagnosticCheck(
            name="LDAP Connectivity", passed=True, status="PASSED",
            code=DiagnosticCode.OK.value, severity="info",
            detail="All configured LDAP profiles are reachable.",
            evidence=f"Tested {len(configs)} profile(s)", action=None
        )

    async def _check_group_membership(self, username: str, firewall_id: str) -> tuple[DiagnosticCheck, list[str]]:
        groups = await self.provider.get_user_groups(username, firewall_id)
        if not groups:
            return DiagnosticCheck(
                name="Group Membership", passed=False, status="WARNING",
                code=DiagnosticCode.GROUP_MAPPING_EMPTY.value, severity="medium",
                detail="User has no active group memberships retrieved.",
                evidence="0 group memberships found for user", action="Verify Active Directory group assignments."
            ), groups
        return DiagnosticCheck(
            name="Group Membership", passed=True, status="PASSED",
            code=DiagnosticCode.OK.value, severity="info",
            detail=f"User belongs to {len(groups)} group(s).",
            evidence=f"Groups: {groups[:5]}{'...' if len(groups)>5 else ''}", action=None
        ), groups

    async def _check_group_mapping_freshness(self, firewall_id: str) -> DiagnosticCheck:
        state = await self.provider.get_group_mapping_state(firewall_id)
        if state.status == 'empty' or not state.mapped_groups:
            return DiagnosticCheck(
                name="Group Mapping Freshness", passed=False, status="FAILED",
                code=DiagnosticCode.GROUP_MAPPING_EMPTY.value, severity="high",
                detail="No group mappings synced to firewall.",
                evidence="Group mapping list is empty", action="Trigger PAN-OS group mapping sync."
            )
        if state.status == 'stale' or (state.age_hours and state.age_hours > self.settings.group_mapping_stale_hours):
            age_str = f"{state.age_hours:.1f}" if state.age_hours else "unknown"
            return DiagnosticCheck(
                name="Group Mapping Freshness", passed=False, status="WARNING",
                code=DiagnosticCode.GROUP_MAPPING_STALE.value, severity="medium",
                detail=f"Group mappings are stale (last synced {age_str} hours ago).",
                evidence=f"Sync status: {state.status}, age: {age_str}h", action="Verify LDAP group refresh interval."
            )
        return DiagnosticCheck(
            name="Group Mapping Freshness", passed=True, status="PASSED",
            code=DiagnosticCode.OK.value, severity="info",
            detail="Group mappings are fresh.",
            evidence=f"Mapped groups count: {len(state.mapped_groups)}", action=None
        )

    async def _check_auth_history(self, username: str, firewall_id: str) -> DiagnosticCheck:
        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            return DiagnosticCheck(
                name="Authentication History", passed=True, status="PASSED",
                code=DiagnosticCode.OK.value, severity="info",
                detail="Cannot verify auth history for unknown user.",
                evidence="User missing from DB", action=None
            )
            
        recent = datetime.now(timezone.utc).timestamp() - (self.settings.auth_failure_window_hours * 3600)
        recent_dt = datetime.fromtimestamp(recent, timezone.utc)
        
        result = await self.db.execute(
            select(AuthenticationEvent)
            .where(
                and_(
                    AuthenticationEvent.user_id == user.id,
                    AuthenticationEvent.firewall_id == firewall_id,
                    AuthenticationEvent.occurred_at >= recent_dt,
                    AuthenticationEvent.result == 'failure'
                )
            )
        )
        failures = result.scalars().all()
        if len(failures) >= self.settings.auth_failure_threshold:
            return DiagnosticCheck(
                name="Authentication History", passed=False, status="WARNING",
                code=DiagnosticCode.AUTHENTICATION_FAILURE.value, severity="medium",
                detail=f"Found {len(failures)} recent authentication failures in last {self.settings.auth_failure_window_hours}h.",
                evidence=f"{len(failures)} failure events recorded", action="Review authentication logs for bad password or account lockout."
            )
            
        return DiagnosticCheck(
            name="Authentication History", passed=True, status="PASSED",
            code=DiagnosticCode.OK.value, severity="info",
            detail="No excessive authentication failures detected.",
            evidence=f"{len(failures)} failure events in window", action=None
        )

    async def _check_identity_consistency(self, username: str, firewall_id: str) -> DiagnosticCheck:
        # Check if user has conflicting IP mappings across different firewalls
        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user:
            ip_res = await self.db.execute(
                select(UserIPMapping)
                .where(UserIPMapping.user_id == user.id, UserIPMapping.is_current == True)
            )
            current_mappings = ip_res.scalars().all()
            unique_ips = set(m.ip_address for m in current_mappings)
            if len(unique_ips) > 1:
                return DiagnosticCheck(
                    name="Identity Consistency", passed=False, status="WARNING",
                    code=DiagnosticCode.IDENTITY_INCONSISTENT.value, severity="high",
                    detail=f"Conflicting IP mappings detected across firewalls: {list(unique_ips)}",
                    evidence=f"User mapped to {len(unique_ips)} different IPs concurrently",
                    action="Check for IP address overlap or stale User-ID mapping sessions."
                )

        return DiagnosticCheck(
            name="Identity Consistency", passed=True, status="PASSED",
            code=DiagnosticCode.OK.value, severity="info",
            detail="Identity appears consistent across environment.",
            evidence="No conflicting IP mappings detected", action=None
        )

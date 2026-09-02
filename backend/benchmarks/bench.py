import os
import time
import asyncio
import statistics
import click
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func, text, or_

from app.config import get_settings
from app.models import User, Group, Firewall, UserIPMapping, AuthenticationEvent, UserGroupMembership
from app.providers.mock import MockPaloAltoProvider
from app.services.diagnostics import DiagnosticEngine

def calculate_percentiles(durations_ms: list[float]) -> dict[str, float]:
    if not durations_ms:
        return {"min": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0, "qps": 0}
    sorted_d = sorted(durations_ms)
    n = len(sorted_d)
    return {
        "min": round(sorted_d[0], 2),
        "p50": round(sorted_d[int(n * 0.50)], 2),
        "p95": round(sorted_d[min(n - 1, int(n * 0.95))], 2),
        "p99": round(sorted_d[min(n - 1, int(n * 0.99))], 2),
        "max": round(sorted_d[-1], 2),
        "qps": round(1000.0 / (sum(durations_ms) / n), 1) if sum(durations_ms) > 0 else 0
    }

async def run_benchmark(preset: str, iterations: int):
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # Fetch sample data for queries
        user_res = await db.execute(select(User).limit(100))
        sample_users = user_res.scalars().all()
        if not sample_users:
            print("ERROR: Database appears empty. Please run data generator first!")
            return

        fw_res = await db.execute(select(Firewall).limit(20))
        sample_firewalls = fw_res.scalars().all()

        ip_res = await db.execute(select(UserIPMapping).limit(50))
        sample_ips = ip_res.scalars().all()

        scenarios = {}

        # 1. Exact Username Lookup
        durations = []
        for i in range(iterations):
            u = sample_users[i % len(sample_users)]
            t0 = time.perf_counter()
            res = await db.execute(select(User).where(User.username == u.username))
            _ = res.scalar_one_or_none()
            durations.append((time.perf_counter() - t0) * 1000)
        scenarios["Exact Username Lookup"] = calculate_percentiles(durations)

        # 2. Exact Email Lookup
        durations = []
        for i in range(iterations):
            u = sample_users[i % len(sample_users)]
            t0 = time.perf_counter()
            res = await db.execute(select(User).where(User.email == u.email))
            _ = res.scalar_one_or_none()
            durations.append((time.perf_counter() - t0) * 1000)
        scenarios["Exact Email Lookup"] = calculate_percentiles(durations)

        # 3. IP Mapping Lookup
        if sample_ips:
            durations = []
            for i in range(iterations):
                ip_item = sample_ips[i % len(sample_ips)]
                t0 = time.perf_counter()
                res = await db.execute(select(UserIPMapping).where(UserIPMapping.ip_address == ip_item.ip_address))
                _ = res.scalars().all()
                durations.append((time.perf_counter() - t0) * 1000)
            scenarios["IP Address Lookup"] = calculate_percentiles(durations)

        # 4. Firewall Hostname Lookup
        if sample_firewalls:
            durations = []
            for i in range(iterations):
                fw = sample_firewalls[i % len(sample_firewalls)]
                t0 = time.perf_counter()
                res = await db.execute(select(Firewall).where(Firewall.hostname == fw.hostname))
                _ = res.scalar_one_or_none()
                durations.append((time.perf_counter() - t0) * 1000)
            scenarios["Firewall Hostname Lookup"] = calculate_percentiles(durations)

        # 5. User Group Memberships Join
        durations = []
        for i in range(iterations):
            u = sample_users[i % len(sample_users)]
            t0 = time.perf_counter()
            res = await db.execute(
                select(Group).join(UserGroupMembership).where(UserGroupMembership.user_id == u.id)
            )
            _ = res.scalars().all()
            durations.append((time.perf_counter() - t0) * 1000)
        scenarios["User Group Memberships Join"] = calculate_percentiles(durations)

        # 6. Auth Events Keyset Pagination
        durations = []
        for i in range(iterations):
            u = sample_users[i % len(sample_users)]
            t0 = time.perf_counter()
            res = await db.execute(
                select(AuthenticationEvent)
                .where(AuthenticationEvent.user_id == u.id)
                .order_by(AuthenticationEvent.occurred_at.desc(), AuthenticationEvent.id.desc())
                .limit(50)
            )
            _ = res.scalars().all()
            durations.append((time.perf_counter() - t0) * 1000)
        scenarios["Auth Events Keyset Query"] = calculate_percentiles(durations)

        # 7. Full Diagnostic Run
        if sample_firewalls:
            provider = MockPaloAltoProvider(db)
            diag_engine = DiagnosticEngine(provider=provider, db=db, settings=settings)
            durations = []
            for i in range(min(iterations, 100)):  # Diagnostic involves multiple DB queries
                u = sample_users[i % len(sample_users)]
                fw = sample_firewalls[i % len(sample_firewalls)]
                t0 = time.perf_counter()
                _ = await diag_engine.run_user_diagnostic(str(fw.id), u.username, "benchmarking_harness")
                durations.append((time.perf_counter() - t0) * 1000)
            scenarios["Full Diagnostic Run (9 Checks)"] = calculate_percentiles(durations)

    await engine.dispose()

    # Output Markdown Report
    print(f"\n### Performance Benchmark Results (Preset: {preset}, Iterations: {iterations})\n")
    print("| Scenario | Min (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) | QPS |")
    print("|---|---|---|---|---|---|---|")
    for name, stats in scenarios.items():
        print(f"| {name} | {stats['min']} | {stats['p50']} | {stats['p95']} | {stats['p99']} | {stats['max']} | {stats['qps']} |")

@click.command()
@click.option('--preset', type=click.Choice(['dev', 'medium', 'large', 'stress']), default='dev')
@click.option('--iterations', type=int, default=100)
def benchmark(preset, iterations):
    asyncio.run(run_benchmark(preset, iterations))

if __name__ == "__main__":
    benchmark()

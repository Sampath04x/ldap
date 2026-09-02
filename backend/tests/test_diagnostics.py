import pytest
from app.services.diagnostics import DiagnosticEngine
from app.providers.mock import MockPaloAltoProvider
from app.config import get_settings

@pytest.mark.asyncio
async def test_diagnostic_engine_init(test_db):
    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    assert engine.provider == provider

@pytest.mark.asyncio
async def test_diagnostic_engine_run(test_db):
    provider = MockPaloAltoProvider(test_db)
    engine = DiagnosticEngine(provider, test_db, get_settings())
    # Try running it with fake data. It will fail gracefully because no data exists in SQLite memory db.
    import uuid
    fw_id = str(uuid.uuid4())
    res = await engine.run_user_diagnostic(fw_id, "test_user", "test_actor")
    assert res.overall_result == "FIREWALL_UNREACHABLE"
    assert res.overall_status == "FAILED"

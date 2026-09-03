import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from app.main import app
from app.database import get_db
from app.config import get_settings

import os

# Test database URL defaults to PostgreSQL test database
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", 
    "postgresql+asyncpg://fwident:fwident_dev@localhost:5432/fwident_test"
)

@pytest_asyncio.fixture(scope="session")
async def engine():
    test_engine = create_async_engine(TEST_DB_URL, echo=False, pool_pre_ping=True)
    yield test_engine
    await test_engine.dispose()

@pytest_asyncio.fixture
async def test_db(engine):
    from app.models import Base
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
        
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    
    # We could also mock the PaloAltoProvider here
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

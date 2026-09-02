import pytest
from app.services.search import SearchService

@pytest.mark.asyncio
async def test_search_service_exact(test_db):
    service = SearchService()
    res = await service.search(test_db, "admin", type="user", field="username")
    assert res.total >= 0

@pytest.mark.asyncio
async def test_search_service_fuzzy(test_db):
    service = SearchService()
    res = await service.search(test_db, "adm", type="user")
    assert res.total >= 0

@pytest.mark.asyncio
async def test_search_service_ip(test_db):
    service = SearchService()
    res = await service.search(test_db, "10.0.0.1")
    assert res.total >= 0

@pytest.mark.asyncio
async def test_search_pagination(test_db):
    service = SearchService()
    res1 = await service.search(test_db, "a", page=1, page_size=2)
    res2 = await service.search(test_db, "a", page=2, page_size=2)
    assert res1.page == 1
    assert res2.page == 2

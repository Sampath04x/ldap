from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import SearchResult
from app.services.search import SearchService

router = APIRouter()

@router.get("/search", response_model=SearchResult)
async def search_api(
    q: str,
    type: str = Query('all'),
    field: str = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort: str = Query(None),
    order: str = Query('asc'),
    db: AsyncSession = Depends(get_db)
):
    service = SearchService()
    return await service.search(db, q, type, field, status, page, page_size, sort, order)

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.schemas import HealthResponse
from app.config import get_settings

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    settings = get_settings()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_connected=db_ok,
        provider=settings.provider,
        version="1.0.0"
    )

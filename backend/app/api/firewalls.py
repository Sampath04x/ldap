from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db
from app.models import Firewall, LDAPServer
from app.schemas import FirewallResponse, FirewallSummary, LDAPServerResponse, OffsetPageResponse, ErrorResponse
from app.providers import get_provider

router = APIRouter()

@router.get("", response_model=OffsetPageResponse[FirewallSummary])
async def list_firewalls(
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    base_query = select(Firewall)
    if status:
        base_query = base_query.where(Firewall.status == status)
    
    count_query = select(func.count()).select_from(base_query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar_one_or_none() or 0

    base_query = base_query.order_by(Firewall.hostname.asc(), Firewall.id.asc())
    offset = (page - 1) * page_size
    query = base_query.limit(page_size).offset(offset)
    
    res = await db.execute(query)
    items = res.scalars().all()
    has_more = (offset + len(items)) < total
    
    return OffsetPageResponse(items=items, total=total, page=page, page_size=page_size, has_more=has_more)

@router.get("/{id}", response_model=FirewallResponse, responses={404: {"model": ErrorResponse}})
async def get_firewall(id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Firewall).where(Firewall.id == id))
    fw = result.scalar_one_or_none()
    if not fw:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Firewall not found"}})
    return fw

@router.get("/{id}/health")
async def get_firewall_health(id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Firewall).where(Firewall.id == id))
    fw = result.scalar_one_or_none()
    if not fw:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Firewall not found"}})
        
    provider = get_provider(db)
    status = await provider.get_firewall_status(str(id))
    return status

@router.get("/{id}/ldap", response_model=list[LDAPServerResponse])
async def get_firewall_ldap(id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Firewall).where(Firewall.id == id))
    fw = result.scalar_one_or_none()
    if not fw:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Firewall not found"}})
        
    result = await db.execute(select(LDAPServer).where(LDAPServer.firewall_id == id))
    return result.scalars().all()

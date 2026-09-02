from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models import Firewall, LDAPServer
from app.schemas import FirewallResponse, FirewallSummary, LDAPServerResponse, PagedResponse, ErrorResponse
from app.providers import get_provider

router = APIRouter()

@router.get("", response_model=PagedResponse[FirewallSummary])
async def list_firewalls(
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Firewall)
    if status:
        query = query.where(Firewall.status == status)
    
    offset = (page - 1) * page_size
    query = query.limit(page_size + 1).offset(offset)
    
    res = await db.execute(query)
    items = res.scalars().all()
    
    has_more = len(items) > page_size
    items = items[:page_size]
    
    return PagedResponse(items=items, has_more=has_more)

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

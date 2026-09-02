from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.models import User, UserGroupMembership, Group, UserIPMapping, AuthenticationEvent
from app.schemas import UserResponse, GroupSummary, UserIPMappingResponse, AuthEventResponse, PagedResponse, KeysetCursor, ErrorResponse

router = APIRouter()

@router.get("/{username}", response_model=UserResponse, responses={404: {"model": ErrorResponse}})
async def get_user(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"User {username} not found"}})
    return user

@router.get("/{username}/groups", response_model=list[GroupSummary])
async def get_user_groups(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "User not found"}})
        
    result = await db.execute(
        select(Group)
        .join(UserGroupMembership)
        .where(UserGroupMembership.user_id == user.id)
    )
    return result.scalars().all()

@router.get("/{username}/mappings", response_model=list[UserIPMappingResponse])
async def get_user_mappings(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "User not found"}})
        
    result = await db.execute(
        select(UserIPMapping)
        .where(UserIPMapping.user_id == user.id)
        .order_by(UserIPMapping.mapped_at.desc())
    )
    return result.scalars().all()

@router.get("/{username}/events", response_model=PagedResponse[AuthEventResponse])
async def get_user_events(
    username: str,
    after_id: int = Query(None),
    after_ts: datetime = Query(None),
    page_size: int = Query(50, ge=1, le=200),
    result_filter: str = Query(None, alias="result"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "User not found"}})
        
    query = select(AuthenticationEvent).where(AuthenticationEvent.user_id == user.id)
    
    if result_filter:
        query = query.where(AuthenticationEvent.result == result_filter)
        
    if after_id is not None and after_ts is not None:
        query = query.where(
            or_(
                AuthenticationEvent.occurred_at < after_ts,
                and_(AuthenticationEvent.occurred_at == after_ts, AuthenticationEvent.id < after_id)
            )
        )
    
    query = query.order_by(AuthenticationEvent.occurred_at.desc(), AuthenticationEvent.id.desc()).limit(page_size + 1)
    
    res = await db.execute(query)
    items = res.scalars().all()
    
    has_more = len(items) > page_size
    items = items[:page_size]
    
    next_cursor = None
    if has_more and items:
        last_item = items[-1]
        next_cursor = KeysetCursor(after_id=last_item.id, after_ts=last_item.occurred_at)
        
    return PagedResponse(items=items, has_more=has_more, next_cursor=next_cursor)

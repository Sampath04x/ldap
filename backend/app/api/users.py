from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import joinedload
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.models import User, UserGroupMembership, Group, UserIPMapping, AuthenticationEvent
from app.schemas import UserResponse, GroupSummary, UserIPMappingResponse, AuthEventResponse, PagedResponse, OffsetPageResponse, KeysetCursor, ErrorResponse

router = APIRouter()

@router.get("/{username}", response_model=UserResponse, responses={404: {"model": ErrorResponse}})
async def get_user(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"User {username} not found"}})
    return user

@router.get("/{username}/groups", response_model=OffsetPageResponse[GroupSummary])
async def get_user_groups(
    username: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "User not found"}})
        
    base_query = (
        select(Group)
        .join(UserGroupMembership)
        .where(UserGroupMembership.user_id == user.id)
    )
    count_query = select(func.count()).select_from(base_query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar_one_or_none() or 0

    base_query = base_query.order_by(Group.group_name.asc())
    offset = (page - 1) * page_size
    res = await db.execute(base_query.offset(offset).limit(page_size))
    items = res.scalars().all()
    has_more = (offset + len(items)) < total
    return OffsetPageResponse(items=items, total=total, page=page, page_size=page_size, has_more=has_more)

@router.get("/{username}/mappings", response_model=OffsetPageResponse[UserIPMappingResponse])
async def get_user_mappings(
    username: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "User not found"}})
        
    base_query = select(UserIPMapping).where(UserIPMapping.user_id == user.id)
    count_query = select(func.count()).select_from(base_query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar_one_or_none() or 0

    base_query = base_query.order_by(UserIPMapping.mapped_at.desc(), UserIPMapping.id.desc())
    offset = (page - 1) * page_size
    res = await db.execute(base_query.offset(offset).limit(page_size))
    items = res.scalars().all()
    has_more = (offset + len(items)) < total
    return OffsetPageResponse(items=items, total=total, page=page, page_size=page_size, has_more=has_more)

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

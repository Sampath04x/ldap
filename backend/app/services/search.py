from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, asc
from app.models import User, Firewall, Group, UserIPMapping
from app.schemas import SearchResult, SearchItem
import re

class SearchService:
    async def search(self, db: AsyncSession, q: str, type: str = 'all', field: str = None, 
                     status: str = None, page: int = 1, page_size: int = 25, 
                     sort: str = None, order: str = 'asc') -> SearchResult:
        
        offset = (page - 1) * page_size
        is_ip = bool(re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', q))
        
        items = []
        total = 0

        # Handle specific target searches
        if type == 'user' or (field in ('username', 'email', 'ip')):
            items, total = await self._search_users_paginated(db, q, field, is_ip, status, page_size, offset, sort, order)
        elif type == 'firewall' or (field == 'hostname'):
            items, total = await self._search_firewalls_paginated(db, q, field, status, page_size, offset, sort, order)
        elif type == 'group' or (field == 'group_name'):
            items, total = await self._search_groups_paginated(db, q, field, status, page_size, offset, sort, order)
        else:
            # Type is 'all': fetch candidate slices up to page_size from each category for current offset
            per_cat_limit = max(page_size, 10)
            user_items, user_total = await self._search_users_paginated(db, q, field, is_ip, status, per_cat_limit, offset, sort, order)
            fw_items, fw_total = await self._search_firewalls_paginated(db, q, field, status, per_cat_limit, offset, sort, order)
            grp_items, grp_total = await self._search_groups_paginated(db, q, field, status, per_cat_limit, offset, sort, order)
            
            all_items = user_items + fw_items + grp_items
            all_items.sort(key=lambda x: x.score, reverse=True)
            total = user_total + fw_total + grp_total
            items = all_items[:page_size]

        return SearchResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=offset + page_size < total
        )

    async def _search_users_paginated(self, db: AsyncSession, q: str, field: str | None, is_ip: bool, 
                                      status: str | None, limit: int, offset: int, 
                                      sort: str | None, order: str) -> tuple[list[SearchItem], int]:
        base_query = select(User)
        
        if field == 'username':
            base_query = base_query.where(User.username == q)
        elif field == 'email':
            base_query = base_query.where(User.email == q)
        elif field == 'ip' or is_ip:
            base_query = base_query.join(UserIPMapping).where(UserIPMapping.ip_address == q).distinct()
        else:
            safe_q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            base_query = base_query.where(
                or_(
                    User.username.ilike(f"%{safe_q}%"),
                    func.similarity(User.display_name, q) > 0.3
                )
            )
            
        if status:
            base_query = base_query.where(User.status == status)

        # Count total matching
        count_query = select(func.count()).select_from(base_query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar_one_or_none() or 0

        # Apply sorting
        if sort and hasattr(User, sort):
            col = getattr(User, sort)
            base_query = base_query.order_by(desc(col) if order.lower() == 'desc' else asc(col))
        else:
            base_query = base_query.order_by(User.username.asc())

        # Apply DB pagination
        res = await db.execute(base_query.offset(offset).limit(limit))
        users = res.scalars().all()

        items = [
            SearchItem(
                type='user',
                score=1.0 if u.username == q else 0.5,
                data={
                    "id": str(u.id), 
                    "username": u.username, 
                    "email": u.email, 
                    "display_name": u.display_name, 
                    "department": u.department,
                    "job_title": u.job_title,
                    "location": u.location,
                    "status": u.status
                }
            ) for u in users
        ]
        return items, total

    async def _search_firewalls_paginated(self, db: AsyncSession, q: str, field: str | None, 
                                          status: str | None, limit: int, offset: int, 
                                          sort: str | None, order: str) -> tuple[list[SearchItem], int]:
        base_query = select(Firewall)
        if field == 'hostname' or q:
            safe_q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            base_query = base_query.where(Firewall.hostname.ilike(f"%{safe_q}%"))
        if status:
            base_query = base_query.where(Firewall.status == status)

        count_query = select(func.count()).select_from(base_query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar_one_or_none() or 0

        if sort and hasattr(Firewall, sort):
            col = getattr(Firewall, sort)
            base_query = base_query.order_by(desc(col) if order.lower() == 'desc' else asc(col))
        else:
            base_query = base_query.order_by(Firewall.hostname.asc())

        res = await db.execute(base_query.offset(offset).limit(limit))
        firewalls = res.scalars().all()

        items = [
            SearchItem(
                type='firewall',
                score=1.0 if f.hostname == q else 0.5,
                data={
                    "id": str(f.id), 
                    "hostname": f.hostname, 
                    "ip_address": f.ip_address, 
                    "model": f.model,
                    "software_version": f.software_version,
                    "environment": f.environment,
                    "location": f.location,
                    "status": f.status
                }
            ) for f in firewalls
        ]
        return items, total

    async def _search_groups_paginated(self, db: AsyncSession, q: str, field: str | None, 
                                       status: str | None, limit: int, offset: int, 
                                       sort: str | None, order: str) -> tuple[list[SearchItem], int]:
        base_query = select(Group)
        if field == 'group_name' or q:
            safe_q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            base_query = base_query.where(Group.group_name.ilike(f"%{safe_q}%"))
        if status:
            base_query = base_query.where(Group.status == status)

        count_query = select(func.count()).select_from(base_query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar_one_or_none() or 0

        if sort and hasattr(Group, sort):
            col = getattr(Group, sort)
            base_query = base_query.order_by(desc(col) if order.lower() == 'desc' else asc(col))
        else:
            base_query = base_query.order_by(Group.group_name.asc())

        res = await db.execute(base_query.offset(offset).limit(limit))
        groups = res.scalars().all()

        items = [
            SearchItem(
                type='group',
                score=1.0 if g.group_name == q else 0.5,
                data={"id": str(g.id), "group_name": g.group_name, "status": g.status}
            ) for g in groups
        ]
        return items, total

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models import User, Firewall, Group, UserIPMapping
from app.schemas import SearchResult, SearchItem
import re

class SearchService:
    async def search(self, db: AsyncSession, q: str, type: str = 'all', field: str = None, 
                     status: str = None, page: int = 1, page_size: int = 25, 
                     sort: str = None, order: str = 'asc') -> SearchResult:
        
        items = []
        is_ip = bool(re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', q))
        offset = (page - 1) * page_size
        
        if field:
            if field == 'username' and type in ('all', 'user'):
                items.extend(await self._search_users(db, q, True, status))
            elif field == 'email' and type in ('all', 'user'):
                items.extend(await self._search_users_by_email(db, q, status))
            elif field == 'ip' and type in ('all', 'user'):
                items.extend(await self._search_by_ip(db, q, status))
            elif field == 'hostname' and type in ('all', 'firewall'):
                items.extend(await self._search_firewalls(db, q, True, status))
            elif field == 'group_name' and type in ('all', 'group'):
                items.extend(await self._search_groups(db, q, True, status))
        else:
            if is_ip and type in ('all', 'user'):
                items.extend(await self._search_by_ip(db, q, status))
            else:
                if type in ('all', 'user'):
                    items.extend(await self._search_users(db, q, False, status))
                if type in ('all', 'firewall'):
                    items.extend(await self._search_firewalls(db, q, False, status))
                if type in ('all', 'group'):
                    items.extend(await self._search_groups(db, q, False, status))

        items.sort(key=lambda x: x.score, reverse=True)
        total = len(items)
        paginated_items = items[offset:offset + page_size]
        
        return SearchResult(
            items=paginated_items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=offset + page_size < total
        )

    async def _search_users(self, db: AsyncSession, q: str, exact: bool, status: str = None) -> list[SearchItem]:
        query = select(User)
        if exact:
            query = query.where(User.username == q)
        else:
            safe_q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            query = query.where(
                or_(
                    User.username.ilike(f"%{safe_q}%"),
                    func.similarity(User.display_name, q) > 0.3
                )
            )
        if status:
            query = query.where(User.status == status)
        
        result = await db.execute(query.limit(50))
        return [
            SearchItem(
                type='user',
                score=1.0 if u.username == q else 0.5,
                data={"id": str(u.id), "username": u.username, "display_name": u.display_name, "status": u.status}
            ) for u in result.scalars().all()
        ]

    async def _search_users_by_email(self, db: AsyncSession, q: str, status: str = None) -> list[SearchItem]:
        query = select(User).where(User.email == q)
        if status:
            query = query.where(User.status == status)
        result = await db.execute(query.limit(50))
        return [
            SearchItem(
                type='user',
                score=1.0,
                data={"id": str(u.id), "username": u.username, "display_name": u.display_name, "status": u.status}
            ) for u in result.scalars().all()
        ]

    async def _search_firewalls(self, db: AsyncSession, q: str, exact: bool, status: str = None) -> list[SearchItem]:
        query = select(Firewall)
        if exact:
            query = query.where(Firewall.hostname == q)
        else:
            safe_q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            query = query.where(Firewall.hostname.ilike(f"%{safe_q}%"))
        if status:
            query = query.where(Firewall.status == status)
        
        result = await db.execute(query.limit(50))
        return [
            SearchItem(
                type='firewall',
                score=1.0 if f.hostname == q else 0.5,
                data={"id": str(f.id), "hostname": f.hostname, "ip_address": f.ip_address, "status": f.status}
            ) for f in result.scalars().all()
        ]

    async def _search_groups(self, db: AsyncSession, q: str, exact: bool, status: str = None) -> list[SearchItem]:
        query = select(Group)
        if exact:
            query = query.where(Group.group_name == q)
        else:
            safe_q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            query = query.where(Group.group_name.ilike(f"%{safe_q}%"))
        if status:
            query = query.where(Group.status == status)
            
        result = await db.execute(query.limit(50))
        return [
            SearchItem(
                type='group',
                score=1.0 if g.group_name == q else 0.5,
                data={"id": str(g.id), "group_name": g.group_name, "status": g.status}
            ) for g in result.scalars().all()
        ]
        
    async def _search_by_ip(self, db: AsyncSession, ip: str, status: str = None) -> list[SearchItem]:
        query = select(User).join(UserIPMapping).where(UserIPMapping.ip_address == ip)
        if status:
            query = query.where(User.status == status)
        
        result = await db.execute(query.limit(50))
        return [
            SearchItem(
                type='user',
                score=1.0,
                data={"id": str(u.id), "username": u.username, "display_name": u.display_name, "status": u.status}
            ) for u in result.scalars().all()
        ]

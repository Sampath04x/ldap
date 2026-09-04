import uuid
import json
from datetime import datetime, timezone
from fastapi import Request, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.database import AsyncSessionLocal
from app.models import AuditLog

async def log_audit_event(
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    request_ip: str,
    request_id: str,
    extra: dict
):
    async with AsyncSessionLocal() as session:
        log = AuditLog(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_ip=request_ip,
            request_id=request_id,
            extra=extra,
            occurred_at=datetime.now(timezone.utc)
        )
        session.add(log)
        await session.commit()

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        actor = request.headers.get("X-API-Key", "anonymous")
        action = f"{request.method} {request.url.path}"
        resource_type = "api"
        resource_id = request.url.path
        request_ip = request.client.host if request.client else None
        
        extra = {
            "query": str(request.query_params),
            "status_code": response.status_code
        }
        
        try:
            await log_audit_event(
                actor=actor,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                request_ip=request_ip,
                request_id=request_id,
                extra=extra
            )
        except Exception as e:
            import logging
            logging.error(f"Failed to record audit log: {e}")

        return response

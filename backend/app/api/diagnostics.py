from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.config import get_settings, Settings
from app.models import DiagnosticRun
from app.schemas import DiagnosticUserRequest, DiagnosticRunResponse, ErrorResponse
from app.providers import get_provider
from app.services.diagnostics import DiagnosticEngine

router = APIRouter()

@router.post("/user", response_model=DiagnosticRunResponse)
async def run_user_diagnostic(
    req: DiagnosticUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    actor = request.headers.get("X-API-Key", "anonymous")
    settings = get_settings()
    provider = get_provider(db)
    
    engine = DiagnosticEngine(provider=provider, db=db, settings=settings)
    return await engine.run_user_diagnostic(str(req.firewall_id), req.username, triggered_by=actor)

@router.get("/{run_id}", response_model=DiagnosticRunResponse, responses={404: {"model": ErrorResponse}})
async def get_diagnostic_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DiagnosticRun).where(DiagnosticRun.id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Diagnostic run not found"}})
        
    # Reconstruct the response schema from DB model
    # Convert dicts from JSON to DiagnosticCheck
    from app.schemas import DiagnosticCheck
    checks = [DiagnosticCheck(**c) for c in run.results_json]
    
    # We need firewall hostname, for simplicity we just fetch it
    from app.models import Firewall
    fw_res = await db.execute(select(Firewall).where(Firewall.id == run.subject_firewall_id))
    fw = fw_res.scalar_one_or_none()
    fw_name = fw.hostname if fw else str(run.subject_firewall_id)

    return DiagnosticRunResponse(
        run_id=run.id,
        subject=run.subject_username or "",
        firewall=fw_name,
        overall_result=run.overall_result,
        overall_status=run.overall_status,
        duration_ms=run.duration_ms,
        checks=checks,
        summary=f"Diagnostic run completed with status {run.overall_status}.",
        created_at=run.created_at
    )

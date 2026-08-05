from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.result import AnalysisResult
from app.models.job import Job

router = APIRouter(prefix="/api/v1", tags=["JSON API"])
api_key_header = APIKeyHeader(name="X-API-Key")

async def get_tenant_by_key(api_key: str = Security(api_key_header), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.api_key == api_key))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return tenant

@router.get("/results/{job_id}")
async def get_result_json(
    job_id: str,
    tenant: Tenant = Depends(get_tenant_by_key),
    db: AsyncSession = Depends(get_db)
):
    r = await db.execute(
        select(AnalysisResult).where(AnalysisResult.job_id == job_id, AnalysisResult.tenant_id == tenant.id)
    )
    result = r.scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return {"job_id": job_id, "scores": {
        "overall": result.score_overall, "model": result.score_model,
        "dax": result.score_dax, "visuals": result.score_visuals, "size": result.score_size
    }, "data": result.result_json}

@router.get("/history")
async def get_history(
    tenant: Tenant = Depends(get_tenant_by_key),
    db: AsyncSession = Depends(get_db)
):
    r = await db.execute(
        select(Job, AnalysisResult)
        .join(AnalysisResult, Job.id == AnalysisResult.job_id, isouter=True)
        .where(Job.tenant_id == tenant.id)
        .order_by(Job.created_at.desc())
    )
    rows = r.all()
    return {"history": [{"job_id": row.Job.id, "filename": row.Job.filename, "status": row.Job.status,
        "score_overall": row.AnalysisResult.score_overall if row.AnalysisResult else None,
        "created_at": row.Job.created_at.isoformat()} for row in rows]}

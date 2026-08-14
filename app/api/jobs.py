import uuid, os, aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobStatusResponse, JobListResponse
from app.api.deps import get_current_user
from app.core.config import PLANS
from sqlalchemy import func
from datetime import datetime, timezone
from app.worker.tasks import analyze_pbix_task

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("/upload")
async def upload_pbix(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Quota kontrolü
    from app.models.tenant import Tenant
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant:
        plan_info = PLANS.get(tenant.plan, PLANS["free"])
        quota = plan_info["quota_monthly"]
        now = datetime.now(timezone.utc)
        usage_result = await db.execute(
            select(func.count(Job.id)).where(
                Job.tenant_id == current_user.tenant_id,
                func.extract("year", Job.created_at) == now.year,
                func.extract("month", Job.created_at) == now.month,
            )
        )
        usage = usage_result.scalar() or 0
        # FEEDBACK PHASE: Quota kontrolü devre dışı, unlimited
        # if usage >= quota:
        #     raise HTTPException(status_code=429, detail=f"Monthly quota exceeded ({usage}/{quota}). Upgrade your plan.")

    if not file.filename.endswith(".pbix"):
        raise HTTPException(status_code=400, detail="Only .pbix files accepted")

    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(settings.UPLOAD_DIR, current_user.tenant_id)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{job_id}.pbix")

    # Stream ile diske yaz - RAM'e alma
    size_bytes = 0
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size_bytes += len(chunk)
            if size_bytes > max_bytes:
                await f.close()
                os.remove(file_path)
                raise HTTPException(status_code=413, detail=f"File too large. Max {settings.MAX_UPLOAD_MB} MB")
            await f.write(chunk)

    size_mb = round(size_bytes / (1024 * 1024), 2)

    # DB'ye kaydet
    job = Job(
        id=job_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        filename=file.filename,
        file_size_mb=size_mb,
        status="pending"
    )
    db.add(job)
    await db.commit()

    # Celery kuyruğuna ekle
    analyze_pbix_task.delay(job_id, current_user.tenant_id, file_path)

    return {"job_id": job_id, "filename": file.filename, "size_mb": size_mb, "status": "pending"}

@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.tenant_id == current_user.tenant_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        id=job.id, filename=job.filename, status=job.status,
        file_size_mb=float(job.file_size_mb) if job.file_size_mb else None,
        error_message=job.error_message, started_at=job.started_at,
        completed_at=job.completed_at, created_at=job.created_at
    )

@router.get("/", response_model=JobListResponse)
async def list_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Job).where(Job.tenant_id == current_user.tenant_id).order_by(Job.created_at.desc())
    )
    jobs = result.scalars().all()
    return JobListResponse(
        jobs=[JobStatusResponse(
            id=j.id, filename=j.filename, status=j.status,
            file_size_mb=float(j.file_size_mb) if j.file_size_mb else None,
            error_message=j.error_message, started_at=j.started_at,
            completed_at=j.completed_at, created_at=j.created_at
        ) for j in jobs],
        total=len(jobs)
    )

#!/usr/bin/env python3
"""30 günden eski job'ları ve ilgili dosyaları temizler."""
import os, sys, asyncio
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/home/pbixapp/app")
os.environ.setdefault("PYTHONPATH", "/home/pbixapp/app")

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.job import Job
from app.models.result import AnalysisResult as Result
from app.core.config import settings

RETENTION_DAYS = 30

async def cleanup():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    deleted_jobs = 0
    deleted_files = 0

    async with async_session() as session:
        result = await session.execute(
            select(Job).where(Job.created_at < cutoff)
        )
        old_jobs = result.scalars().all()

        for job in old_jobs:
            result_path = os.path.join(settings.RESULTS_DIR, job.tenant_id, f"{job.id}.json")
            if os.path.exists(result_path):
                os.remove(result_path)
                deleted_files += 1

            upload_path = os.path.join(settings.UPLOAD_DIR, job.tenant_id, f"{job.id}.pbix")
            if os.path.exists(upload_path):
                os.remove(upload_path)
                deleted_files += 1

        if old_jobs:
            job_ids = [j.id for j in old_jobs]
            await session.execute(delete(Result).where(Result.job_id.in_(job_ids)))
            await session.execute(delete(Job).where(Job.id.in_(job_ids)))
            await session.commit()
            deleted_jobs = len(old_jobs)

    print(f"[{datetime.now()}] Cleanup: {deleted_jobs} job, {deleted_files} file silindi.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(cleanup())

import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jinja2 import Environment, FileSystemLoader
from app.core.database import get_db
from app.models.job import Job
from app.models.result import AnalysisResult
from app.models.user import User
from app.api.deps import get_current_user
import os

router = APIRouter(prefix="/reports", tags=["reports"])

def get_jinja_env():
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    return Environment(loader=FileSystemLoader(template_dir))

@router.get("/{job_id}", response_class=HTMLResponse)
async def get_report(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    job = await _get_job(job_id, current_user.tenant_id, db)
    result = await _get_result(job_id, current_user.tenant_id, db)
    env = get_jinja_env()
    template = env.get_template("report.html")
    html = template.render(job=job, result=result.result_json, scores={
        "overall": result.score_overall,
        "model": result.score_model,
        "dax": result.score_dax,
        "visuals": result.score_visuals,
        "size": result.score_size,
    })
    return HTMLResponse(content=html)

@router.get("/{job_id}/pdf")
async def get_report_pdf(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from weasyprint import HTML
    job = await _get_job(job_id, current_user.tenant_id, db)
    result = await _get_result(job_id, current_user.tenant_id, db)
    env = get_jinja_env()
    template = env.get_template("report_pdf.html")
    html_content = template.render(job=job, result=result.result_json, scores={
        "overall": result.score_overall, "model": result.score_model,
        "dax": result.score_dax, "visuals": result.score_visuals, "size": result.score_size,
    })
    pdf_bytes = HTML(string=html_content).write_pdf()
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{job_id}.pdf"}
    )

@router.get("/compare")
async def compare_reports(
    a: str, b: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result_a = await _get_result(a, current_user.tenant_id, db)
    result_b = await _get_result(b, current_user.tenant_id, db)
    return {
        "report_a": {"job_id": a, "scores": {"overall": result_a.score_overall, "model": result_a.score_model, "dax": result_a.score_dax, "visuals": result_a.score_visuals, "size": result_a.score_size}},
        "report_b": {"job_id": b, "scores": {"overall": result_b.score_overall, "model": result_b.score_model, "dax": result_b.score_dax, "visuals": result_b.score_visuals, "size": result_b.score_size}},
    }

async def _get_job(job_id, tenant_id, db):
    r = await db.execute(select(Job).where(Job.id == job_id, Job.tenant_id == tenant_id))
    job = r.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job status: {job.status}")
    return job

async def _get_result(job_id, tenant_id, db):
    r = await db.execute(select(AnalysisResult).where(AnalysisResult.job_id == job_id, AnalysisResult.tenant_id == tenant_id))
    result = r.scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result

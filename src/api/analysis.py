from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from src.api.schemas import AnalysisRunRead, JobRead, ReviewReportRead
from src.api.security import require_api_token
from src.db.models import AnalysisJob, AnalysisRun, ReviewReport
from src.db.session import AsyncSessionLocal

router = APIRouter(prefix="/api/v1", tags=["analysis"], dependencies=[Depends(require_api_token)])


@router.get("/analysis-runs", response_model=list[AnalysisRunRead])
async def list_analysis_runs() -> list[AnalysisRunRead]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AnalysisRun).order_by(AnalysisRun.created_at.desc()))
        return [
            AnalysisRunRead(
                id=run.id,
                snapshot_id=run.snapshot_id,
                status=run.status,
                repository_id=run.repository_id,
                meta_data=run.meta_data,
            )
            for run in result.scalars().all()
        ]


@router.get("/analysis-runs/{analysis_run_id}", response_model=AnalysisRunRead)
async def get_analysis_run(analysis_run_id: str) -> AnalysisRunRead:
    async with AsyncSessionLocal() as session:
        run = await session.get(AnalysisRun, analysis_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis run not found")
        return AnalysisRunRead(
            id=run.id,
            snapshot_id=run.snapshot_id,
            status=run.status,
            repository_id=run.repository_id,
            meta_data=run.meta_data,
        )


@router.get("/analysis-runs/{analysis_run_id}/reports", response_model=list[ReviewReportRead])
async def list_reports(analysis_run_id: str) -> list[ReviewReportRead]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ReviewReport).where(ReviewReport.analysis_run_id == analysis_run_id))
        return [
            ReviewReportRead(
                id=report.id,
                analysis_run_id=report.analysis_run_id,
                tracking_token=report.tracking_token,
                report=report.report,
            )
            for report in result.scalars().all()
        ]


@router.get("/jobs", response_model=list[JobRead])
async def list_jobs() -> list[JobRead]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AnalysisJob).order_by(AnalysisJob.created_at.desc()))
        return [
            JobRead(
                id=job.id,
                status=job.status,
                repository_id=job.repository_id,
                analysis_run_id=job.analysis_run_id,
                attempts=job.attempts,
                last_error=job.last_error,
                payload=job.payload,
            )
            for job in result.scalars().all()
        ]

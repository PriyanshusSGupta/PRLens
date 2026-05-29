from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.pull_request import PullRequest
from app.models.finding import Finding
from app.models.repository import Repository
from app.models.review_run import ReviewRun

router = APIRouter(prefix="/api/prs", tags=["pull_requests"])


@router.get("")
async def list_prs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PullRequest)
        .join(Repository)
        .order_by(PullRequest.risk_score.desc().nullslast(), PullRequest.created_at.desc())
        .limit(50)
    )
    prs = result.scalars().all()

    return [
        {
            "id": pr.id,
            "pr_number": pr.pr_number,
            "title": pr.title,
            "state": pr.state,
            "author": pr.author,
            "risk_score": pr.risk_score,
            "url": pr.url,
            "created_at": str(pr.created_at) if pr.created_at else None,
        }
        for pr in prs
    ]


@router.get("/{pr_id}")
async def get_pr(
    pr_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pr_result = await db.execute(select(PullRequest).where(PullRequest.id == pr_id))
    pr = pr_result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="PR not found")

    findings_result = await db.execute(
        select(Finding).where(Finding.pr_id == pr.id).order_by(
            Finding.severity.desc(), Finding.confidence.desc()
        )
    )
    findings = findings_result.scalars().all()

    runs_result = await db.execute(
        select(ReviewRun).where(ReviewRun.pr_id == pr.id).order_by(ReviewRun.started_at.desc())
    )
    runs = runs_result.scalars().all()

    file_risk = {}
    for f in findings:
        if f.file_path:
            key = f.file_path
            if key not in file_risk:
                file_risk[key] = {"risk": 0.0, "count": 0}
            risk_map = {"critical": 10, "high": 7, "medium": 4, "low": 1}
            file_risk[key]["risk"] += risk_map.get(f.severity, 1) * f.confidence
            file_risk[key]["count"] += 1

    for key in file_risk:
        file_risk[key]["risk"] = round(file_risk[key]["risk"] / 10, 2)

    return {
        "id": pr.id,
        "pr_number": pr.pr_number,
        "title": pr.title,
        "state": pr.state,
        "author": pr.author,
        "risk_score": pr.risk_score,
        "url": pr.url,
        "created_at": str(pr.created_at) if pr.created_at else None,
        "findings_count": len(findings),
        "review_runs": [
            {"id": r.id, "status": r.status, "started_at": str(r.started_at), "findings_count": r.findings_count}
            for r in runs
        ],
        "file_risk": file_risk,
        "findings": [
            {
                "id": f.id,
                "severity": f.severity,
                "category": f.category,
                "file_path": f.file_path,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "message": f.message,
                "suggestion": f.suggestion,
                "confidence": f.confidence,
            }
            for f in findings
        ],
    }


@router.get("/{pr_id}/findings")
async def get_pr_findings(
    pr_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Finding)
        .where(Finding.pr_id == pr_id)
        .order_by(Finding.severity.desc(), Finding.confidence.desc())
    )
    findings = result.scalars().all()
    return {
        "pr_id": pr_id,
        "findings": [
            {
                "id": f.id,
                "severity": f.severity,
                "category": f.category,
                "file_path": f.file_path,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "message": f.message,
                "suggestion": f.suggestion,
                "confidence": f.confidence,
            }
            for f in findings
        ],
    }

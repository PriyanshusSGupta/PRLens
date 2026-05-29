from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.pull_request import PullRequest
from app.models.finding import Finding
from app.models.review_run import ReviewRun

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pr_count = await db.scalar(select(func.count(PullRequest.id)))
    finding_count = await db.scalar(select(func.count(Finding.id)))
    avg_risk = await db.scalar(select(func.avg(PullRequest.risk_score)))

    severity_result = await db.execute(
        select(Finding.severity, func.count(Finding.id)).group_by(Finding.severity)
    )
    findings_by_severity = {row.severity: row[1] for row in severity_result}

    category_result = await db.execute(
        select(Finding.category, func.count(Finding.id)).group_by(Finding.category)
    )
    findings_by_category = {row.category: row[1] for row in category_result}

    recent_result = await db.execute(
        select(PullRequest).order_by(PullRequest.created_at.desc()).limit(5)
    )
    recent_prs = recent_result.scalars().all()

    return {
        "total_prs": pr_count or 0,
        "total_findings": finding_count or 0,
        "avg_risk_score": round(avg_risk or 0.0, 2),
        "findings_by_severity": findings_by_severity,
        "findings_by_category": findings_by_category,
        "recent_prs": [
            {
                "id": pr.id,
                "pr_number": pr.pr_number,
                "title": pr.title,
                "author": pr.author,
                "risk_score": pr.risk_score,
                "state": pr.state,
            }
            for pr in recent_prs
        ],
    }


@router.get("/policy")
async def get_policy(user: User = Depends(get_current_user)):
    from app.core.policy import get_policy as _get_policy
    from app.core.config import settings
    policy = _get_policy()
    return {
        "severity_threshold_block": policy.severity_block,
        "severity_threshold_warn": policy.severity_warn,
        "min_confidence": policy.min_confidence,
        "max_diff_size": policy.max_diff_size,
        "analyzers": {
            "security": policy.enable_security,
            "reliability": policy.enable_reliability,
            "performance": policy.enable_performance,
            "testing": policy.enable_testing,
            "llm": policy.enable_llm,
        },
    }

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.evaluation import EvaluationRun

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


class CreateEvalBody(BaseModel):
    pr_id: int
    prompt_version: str


@router.get("")
async def list_evaluations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(50)
    )
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "pr_id": r.pr_id,
            "prompt_version": r.prompt_version,
            "status": r.status,
            "precision": r.precision,
            "false_positive_rate": r.false_positive_rate,
            "coverage": r.coverage,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in runs
    ]


@router.post("")
async def create_evaluation(
    body: CreateEvalBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = EvaluationRun(
        pr_id=body.pr_id,
        prompt_version=body.prompt_version,
        status="in_progress",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Run review with specified prompt version
    # In production, this would actually re-run the review pipeline
    run.status = "completed"
    await db.commit()

    return {
        "id": run.id,
        "pr_id": run.pr_id,
        "prompt_version": run.prompt_version,
        "status": run.status,
    }

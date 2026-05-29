from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.integrations.github_client import GitHubClient
from app.review_engine import run_review_on_diff
from app.scoring.risk import calculate_risk_score
from app.models.pull_request import PullRequest
from app.models.review_run import ReviewRun
from app.models.finding import Finding
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/review", tags=["review"])


class ReviewRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int

    @field_validator("owner", "repo")
    @classmethod
    def validate_name(cls, v: str) -> str:
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', v):
            raise ValueError("must match GitHub naming rules (letters, digits, hyphens, underscores, dots)")
        return v


@router.post("")
async def manual_review(
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    owner = body.owner
    repo = body.repo
    pr_number = body.pr_number

    client = GitHubClient()
    try:
        pr_data, diff_text = await client.fetch_pr_and_diff(owner, repo, pr_number)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch PR from GitHub: {e}")

    findings = await run_review_on_diff(diff_text, pr_data.get("title", ""), pr_data.get("body", ""))
    risk_score = calculate_risk_score(findings)

    from sqlalchemy import select
    from app.models.repository import Repository
    full_name = f"{owner}/{repo}"
    repo_result = await db.execute(
        select(Repository).where(Repository.full_name == full_name, Repository.active == True)
    )
    repo_row = repo_result.scalar_one_or_none()

    if repo_row:
        pr = PullRequest(
            repo_id=repo_row.id,
            pr_number=pr_number,
            title=pr_data.get("title", ""),
            state=pr_data.get("state", "open"),
            author=pr_data.get("user", {}).get("login", ""),
            base_sha=pr_data.get("base", {}).get("sha", ""),
            head_sha=pr_data.get("head", {}).get("sha", ""),
            url=pr_data.get("html_url", ""),
            risk_score=risk_score,
        )
        db.add(pr)
        await db.flush()

        run = ReviewRun(pr_id=pr.id, status="completed", findings_count=len(findings))
        db.add(run)
        await db.flush()

        for f in findings:
            finding = Finding(
                pr_id=pr.id,
                file_path=f.get("file_path", ""),
                line_start=f.get("line_start"),
                line_end=f.get("line_end"),
                severity=f.get("severity", "low"),
                category=f.get("category", "maintainability"),
                message=f.get("message", ""),
                suggestion=f.get("suggestion"),
                confidence=f.get("confidence", 0.0),
            )
            db.add(finding)
        await db.commit()

    return {
        "pr_number": pr_number,
        "title": pr_data.get("title", ""),
        "author": pr_data.get("user", {}).get("login", ""),
        "state": pr_data.get("state", "open"),
        "risk_score": risk_score,
        "findings": findings,
        "files_changed": pr_data.get("changed_files", 0),
        "pr_id": pr.id if repo_row else None,
    }

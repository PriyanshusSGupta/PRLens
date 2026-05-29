from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.security import verify_github_signature
from app.db.session import get_db
from app.core.crypto import decrypt
from app.integrations.github_client import GitHubClient
from app.models.repository import Repository
from app.models.pull_request import PullRequest
from app.models.review_run import ReviewRun
from app.models.finding import Finding
from app.models.user_token import UserToken
from app.review_engine import run_review_on_diff
from app.scoring.risk import calculate_risk_score

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    signature = request.headers.get("X-Hub-Signature-256", "")
    payload_body = await request.body()
    event_type = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    if event_type not in ("pull_request", "pull_request_review"):
        return {"status": "ignored", "event": event_type}

    action = payload.get("action", "")
    if event_type == "pull_request" and action not in ("opened", "synchronize", "ready_for_review"):
        return {"status": "ignored", "action": action}

    repo_data = payload["repository"]
    pr_data = payload["pull_request"]
    owner = repo_data["owner"]["login"]
    name = repo_data["name"]
    full_name = f"{owner}/{name}"

    repo_result = await db.execute(
        select(Repository).where(Repository.full_name == full_name, Repository.active == True)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository {full_name} not installed")

    if repo.webhook_secret:
        if not verify_github_signature(payload_body, signature, repo.webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")
    else:
        raise HTTPException(status_code=401, detail="Repository has no webhook secret configured")

    existing_pr = (
        await db.execute(
            select(PullRequest).where(
                PullRequest.repo_id == repo.id,
                PullRequest.pr_number == pr_data["number"],
            )
        )
    ).scalar_one_or_none()

    if existing_pr:
        existing_pr.title = pr_data["title"]
        existing_pr.state = pr_data.get("state", "open")
        existing_pr.base_sha = pr_data["base"]["sha"]
        existing_pr.head_sha = pr_data["head"]["sha"]
        existing_pr.url = pr_data.get("html_url")
        pr = existing_pr
    else:
        pr = PullRequest(
            repo_id=repo.id,
            pr_number=pr_data["number"],
            title=pr_data["title"],
            state=pr_data.get("state", "open"),
            author=pr_data["user"]["login"],
            base_sha=pr_data["base"]["sha"],
            head_sha=pr_data["head"]["sha"],
            url=pr_data.get("html_url"),
        )
        db.add(pr)
        await db.flush()

    run = ReviewRun(pr_id=pr.id, status="in_progress")
    db.add(run)
    await db.flush()

    token_result = await db.execute(
        select(UserToken).where(UserToken.provider == "github").order_by(UserToken.created_at.desc()).limit(1)
    )
    user_token = token_result.scalar_one_or_none()
    gh_token = decrypt(user_token.encrypted_token) if user_token else ""

    client = GitHubClient(token=gh_token)
    try:
        _, diff_text = await client.fetch_pr_and_diff(owner, name, pr.pr_number)
    except Exception as e:
        run.status = "failed"
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Failed to fetch PR diff: {e}")

    findings_raw = await run_review_on_diff(diff_text, pr.title)
    risk_score = calculate_risk_score(findings_raw)

    pr.risk_score = risk_score

    for f in findings_raw:
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

    run.status = "completed"
    run.findings_count = len(findings_raw)
    await db.commit()

    try:
        await client.post_pr_comment(owner, name, pr.pr_number, findings_raw)
    except Exception:
        pass

    return {"status": "reviewed", "findings_count": len(findings_raw), "pr_id": pr.id, "run_id": run.id}

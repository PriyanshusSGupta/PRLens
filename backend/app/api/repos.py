import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import get_current_user, require_scope
from app.core.config import settings
from app.core.crypto import decrypt
from app.db.session import get_db
from app.models.user import User
from app.models.user_token import UserToken
from app.models.repository import Repository

router = APIRouter(prefix="/api/repos", tags=["repos"])

GITHUB_API_BASE = "https://api.github.com"


class InstallRepoBody(BaseModel):
    full_name: str


async def _get_user_token(user: User, db: AsyncSession) -> str:
    result = await db.execute(
        select(UserToken).where(UserToken.user_id == user.id, UserToken.provider == "github").order_by(UserToken.created_at.desc()).limit(1)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=401, detail="No GitHub token found. Please re-authenticate.")
    return decrypt(token.encrypted_token)


async def _github_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}


@router.get("")
async def list_repos(
    page: int = 1,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = await _get_user_token(user, db)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API_BASE}/user/repos",
            params={"sort": "updated", "page": page, "per_page": 30},
            headers=await _github_headers(token),
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"GitHub API error: {resp.text}")
    repos = resp.json()
    result = await db.execute(select(Repository).where(Repository.active == True))
    installed = {r.full_name: r for r in result.scalars().all()}
    return [
        {
            "id": r["id"],
            "full_name": r["full_name"],
            "description": r.get("description"),
            "private": r["private"],
            "updated_at": r["updated_at"],
            "installed": r["full_name"] in installed,
            "webhook_status": "active" if r["full_name"] in installed else None,
        }
        for r in repos
    ]


@router.post("/install")
async def install_repo(
    body: InstallRepoBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = await _get_user_token(user, db)
    parts = body.full_name.split("/")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="full_name must be in 'owner/repo' format")
    owner, name = parts

    existing = (
        await db.execute(select(Repository).where(Repository.full_name == body.full_name))
    ).scalar_one_or_none()
    if existing and existing.active:
        return {"status": "already_installed", "webhook_id": existing.webhook_id}

    import secrets
    webhook_secret = secrets.token_hex(32)

    async with httpx.AsyncClient() as client:
        hook_resp = await client.post(
            f"{GITHUB_API_BASE}/repos/{owner}/{name}/hooks",
            json={
                "name": "web",
                "active": True,
                "events": ["pull_request", "pull_request_review"],
                "config": {
                    "url": f"{settings.app_base_url}/api/webhooks/github",
                    "content_type": "json",
                    "secret": webhook_secret,
                },
            },
            headers=await _github_headers(token),
        )
    if hook_resp.status_code == 422:
        raise HTTPException(status_code=400, detail="This repo may already have a PRLens webhook. Remove it manually first.")
    if hook_resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Failed to install webhook: {hook_resp.text}")

    hook_data = hook_resp.json()
    webhook_id = hook_data["id"]

    if existing:
        existing.active = True
        existing.webhook_id = webhook_id
        existing.webhook_secret = webhook_secret
    else:
        repo = Repository(
            owner=owner,
            name=name,
            full_name=body.full_name,
            webhook_id=webhook_id,
            webhook_secret=webhook_secret,
        )
        db.add(repo)
    await db.commit()
    return {"status": "installed", "webhook_id": webhook_id}


@router.post("/uninstall")
async def uninstall_repo(
    body: InstallRepoBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = await _get_user_token(user, db)
    parts = body.full_name.split("/")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="full_name must be in 'owner/repo' format")
    owner, name = parts

    repo = (await db.execute(select(Repository).where(Repository.full_name == body.full_name))).scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not installed")

    if repo.webhook_id:
        try:
            async with httpx.AsyncClient() as client:
                await client.delete(
                    f"{GITHUB_API_BASE}/repos/{owner}/{name}/hooks/{repo.webhook_id}",
                    headers=await _github_headers(token),
                )
        except Exception:
            pass

    repo.active = False
    await db.commit()
    return {"status": "uninstalled"}

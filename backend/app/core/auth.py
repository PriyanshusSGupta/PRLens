import time
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.user_token import UserToken


def _secret() -> str:
    secret = settings.jwt_secret
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is required. Generate one with scripts/generate-keys.sh")
    return secret


def create_session_token(user_id: int, duration_hours: int | None = None) -> str:
    hours = duration_hours or settings.session_duration_hours
    payload = {
        "sub": str(user_id),
        "exp": int(time.time()) + hours * 3600,
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def verify_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get("prlens_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_session_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_scope(*required_scopes: str):
    async def dep(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
        result = await db.execute(
            select(UserToken).where(UserToken.user_id == user.id).order_by(UserToken.created_at.desc()).limit(1)
        )
        token = result.scalar_one_or_none()
        granted = set(token.scope.split(",")) if token and token.scope else set()
        needed = set(required_scopes)
        missing = needed - granted
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required GitHub scopes: {', '.join(sorted(missing))}",
            )
        return user
    return dep

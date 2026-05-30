import datetime
import secrets
import httpx
from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.auth import create_session_token, verify_session_token, get_current_user
from app.core.passwords import hash_password, verify_password
from app.core.email import send_otp, generate_otp
from app.core.crypto import encrypt
from app.db.session import get_db
from app.models.user import User
from app.models.otp_code import OTPCode
from app.models.user_token import UserToken

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_ACCESS_TOKEN = "https://github.com/login/oauth/access_token"
GITHUB_USER_API = "https://api.github.com/user"
GOOGLE_AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_API = "https://www.googleapis.com/oauth2/v2/userinfo"

OAUTH_STATES: TTLCache = TTLCache(maxsize=10000, ttl=600)
EXCHANGE_TOKENS: TTLCache = TTLCache(maxsize=1000, ttl=60)

OTP_EXPIRY_MINUTES = settings.otp_expiry_minutes


class RegisterBody(BaseModel):
    email: EmailStr
    password: str


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class VerifyOtpBody(BaseModel):
    email: EmailStr
    code: str


class ExchangeBody(BaseModel):
    exchange_token: str


def _set_auth_cookie(response: Response, user_id: int):
    session_token = create_session_token(user_id)
    response.set_cookie(
        key="prlens_session",
        value=session_token,
        httponly=True,
        secure=settings.app_base_url.startswith("https"),
        samesite="lax",
        max_age=settings.session_duration_hours * 3600,
        path="/",
    )
    return response


def _assert_configured(client_id: str, client_secret: str, provider: str):
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail=f"{provider} OAuth is not configured.")


def _oauth_redirect(url: str, user_id: int) -> RedirectResponse:
    exchange_token = secrets.token_urlsafe(32)
    EXCHANGE_TOKENS[exchange_token] = user_id
    r = RedirectResponse(url=f"{settings.frontend_url}/auth/success?exchange_token={exchange_token}")
    return r


@router.post("/register")
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing and existing.is_verified:
        raise HTTPException(status_code=400, detail="Email already registered. Please log in instead.")
    if existing and not existing.is_verified:
        await db.execute(delete(OTPCode).where(OTPCode.email == body.email))
        await db.delete(existing)
        await db.flush()
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    code = generate_otp()

    user = User(
        email=body.email,
        hashed_password=await hash_password(body.password),
        is_verified=False,
        auth_provider="email",
    )
    db.add(user)
    await db.flush()

    otp = OTPCode(
        email=body.email,
        code=code,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(otp)
    await db.commit()

    await send_otp(body.email, code)
    return {"message": "Registration started. Check your email for a verification code."}


@router.post("/verify-otp")
@limiter.limit("5/minute")
async def verify_otp(request: Request, body: VerifyOtpBody, response: Response, db: AsyncSession = Depends(get_db)):
    now = datetime.datetime.utcnow()
    result = await db.execute(
        select(OTPCode).where(
            OTPCode.email == body.email,
            OTPCode.used == False,
            OTPCode.expires_at > now,
        ).order_by(OTPCode.created_at.desc())
    )
    otp = result.scalars().first()
    if not otp:
        raise HTTPException(status_code=400, detail="No valid code found. Request a new one.")

    otp.attempts += 1
    if otp.code != body.code or otp.attempts > 5:
        await db.commit()
        if otp.attempts > 5:
            raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")
        raise HTTPException(status_code=400, detail="Invalid code.")

    otp.used = True
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_verified = True
    await db.commit()

    _set_auth_cookie(response, user.id)
    return {"user": {"id": user.id, "email": user.email, "username": user.username}}


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginBody, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not await verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_verified:
        await db.execute(delete(OTPCode).where(OTPCode.email == body.email))
        code = generate_otp()
        otp = OTPCode(
            email=body.email,
            code=code,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES),
        )
        db.add(otp)
        await db.commit()
        await send_otp(body.email, code)
        raise HTTPException(status_code=403, detail="Email not verified. A new code has been sent.")

    _set_auth_cookie(response, user.id)
    return {"user": {"id": user.id, "email": user.email, "username": user.username}}


@router.post("/exchange")
async def exchange_session(body: ExchangeBody, response: Response):
    user_id = EXCHANGE_TOKENS.pop(body.exchange_token, None)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired exchange token.")
    _set_auth_cookie(response, user_id)
    return {"status": "ok"}


@router.get("/google/login")
async def google_login():
    _assert_configured(settings.google_client_id, settings.google_client_secret, "Google")
    state = secrets.token_urlsafe(32)
    OAUTH_STATES[state] = state
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.app_base_url}/api/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return {"redirect_url": f"{GOOGLE_AUTHORIZE}?{qs}"}


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    _assert_configured(settings.google_client_id, settings.google_client_secret, "Google")
    if not OAUTH_STATES.pop(state, None):
        raise HTTPException(status_code=400, detail="Invalid or expired state.")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{settings.app_base_url}/api/auth/google/callback",
        })
        if token_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="OAuth provider error")
        token_data = token_resp.json()
        user_resp = await client.get(GOOGLE_USER_API,
            headers={"Authorization": f"Bearer {token_data['access_token']}"})
        if user_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="OAuth provider error")
        user_data = user_resp.json()

    google_id = user_data["id"]
    email = user_data.get("email", "")
    username = user_data.get("name") or email
    avatar_url = user_data.get("picture", "")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=email, google_id=google_id, username=username, avatar_url=avatar_url,
                    is_verified=True, auth_provider="google")
        db.add(user)
        await db.flush()
    else:
        user.email = email
        user.username = username
        user.avatar_url = avatar_url
    await db.commit()
    return _oauth_redirect(f"{settings.frontend_url}/auth/success", user.id)


@router.get("/github/login")
async def github_login():
    _assert_configured(settings.github_client_id, settings.github_client_secret, "GitHub")
    state = secrets.token_urlsafe(32)
    OAUTH_STATES[state] = state
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.app_base_url}/api/auth/github/callback",
        "scope": "user:email",
        "state": state,
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return {"redirect_url": f"{GITHUB_AUTHORIZE}?{qs}"}


@router.get("/github/callback")
async def github_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    _assert_configured(settings.github_client_id, settings.github_client_secret, "GitHub")
    if not OAUTH_STATES.pop(state, None):
        raise HTTPException(status_code=400, detail="Invalid or expired state.")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GITHUB_ACCESS_TOKEN, json={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": f"{settings.app_base_url}/api/auth/github/callback",
        }, headers={"Accept": "application/json"})
        if token_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="OAuth provider error")
        token_data = token_resp.json()
        access_token = token_data["access_token"]

        user_resp = await client.get(GITHUB_USER_API,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
        if user_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="OAuth provider error")
        user_data = user_resp.json()

        emails_resp = await client.get(f"{GITHUB_USER_API}/emails",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
        emails = emails_resp.json() if emails_resp.status_code == 200 else []
        primary_email = next((e["email"] for e in emails if e.get("primary")), user_data.get("email", ""))

    github_id = user_data["id"]
    username = user_data["login"]
    avatar_url = user_data.get("avatar_url", "")

    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=primary_email, github_id=github_id, username=username, avatar_url=avatar_url,
                    is_verified=True, auth_provider="github")
        db.add(user)
        await db.flush()
    else:
        user.username = username
        user.avatar_url = avatar_url
        if primary_email:
            user.email = primary_email
    await db.commit()
    return _oauth_redirect(f"{settings.frontend_url}/auth/success?github_connect_needed=true", user.id)


@router.get("/github-connect/login")
async def github_connect_login():
    _assert_configured(settings.github_client_id, settings.github_client_secret, "GitHub")
    state = secrets.token_urlsafe(32)
    OAUTH_STATES[state] = state
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.app_base_url}/api/auth/github-connect/callback",
        "scope": "repo:status,pull_requests:read",
        "state": state,
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return {"redirect_url": f"{GITHUB_AUTHORIZE}?{qs}"}


@router.get("/github-connect/callback")
async def github_connect_callback(code: str, state: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    _assert_configured(settings.github_client_id, settings.github_client_secret, "GitHub")
    if not OAUTH_STATES.pop(state, None):
        raise HTTPException(status_code=400, detail="Invalid or expired state.")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GITHUB_ACCESS_TOKEN, json={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": f"{settings.app_base_url}/api/auth/github-connect/callback",
        }, headers={"Accept": "application/json"})
        if token_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="OAuth provider error")
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="No access token returned")
        scopes_header = token_resp.headers.get("X-OAuth-Scopes", "")

    encrypted = encrypt(access_token)
    user_token = UserToken(user_id=user.id, provider="github", scope=scopes_header, encrypted_token=encrypted)
    db.add(user_token)
    await db.commit()
    return RedirectResponse(url=f"{settings.frontend_url}/repos?github_connected=true")


@router.get("/me")
async def auth_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "username": user.username, "avatar_url": user.avatar_url}


@router.get("/scopes")
async def auth_scopes(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    SCOPES_MEANING = {
        "repo:status": "Cannot read PR metadata",
        "pull_requests:read": "Cannot read PR diffs",
    }
    result = await db.execute(
        select(UserToken).where(UserToken.user_id == user.id).order_by(UserToken.created_at.desc()).limit(1)
    )
    token = result.scalar_one_or_none()
    if not token or not token.scope:
        return {"scopes": [], "warnings": list(SCOPES_MEANING.values())}
    scopes_list = [s.strip() for s in token.scope.split(",") if s.strip()]
    granted = set(scopes_list)
    warnings = [msg for scope, msg in SCOPES_MEANING.items() if scope not in granted]
    return {"scopes": sorted(granted), "warnings": warnings}


@router.delete("/logout")
async def auth_logout(response: Response, user: User = Depends(get_current_user)):
    response.delete_cookie("prlens_session", path="/")
    return {"status": "logged_out"}

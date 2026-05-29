from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.crypto import encrypt, decrypt
from app.models.user import User
from app.models.user_ai_config import UserAIConfig

router = APIRouter(prefix="/api/ai", tags=["ai"])

PROVIDER_PRESETS = {
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o",
        "base_url": "https://api.openai.com/v1",
        "docs_url": "https://platform.openai.com/api-keys",
        "env_var": "OPENAI_API_KEY",
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "default_model": "claude-3-5-sonnet-latest",
        "base_url": "https://api.anthropic.com/v1",
        "docs_url": "https://console.anthropic.com/settings/keys",
        "env_var": "ANTHROPIC_API_KEY",
    },
    "groq": {
        "label": "Groq",
        "default_model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "docs_url": "https://console.groq.com/keys",
        "env_var": "GROQ_API_KEY",
    },
    "xai": {
        "label": "xAI (Grok)",
        "default_model": "grok-2-latest",
        "base_url": "https://api.x.ai/v1",
        "docs_url": "https://x.ai/api",
        "env_var": "XAI_API_KEY",
    },
    "deepseek": {
        "label": "DeepSeek",
        "default_model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "docs_url": "https://platform.deepseek.com/api_keys",
        "env_var": "DEEPSEEK_API_KEY",
    },
    "moonshot": {
        "label": "Moonshot (Kimi)",
        "default_model": "moonshot-v1-8k",
        "base_url": "https://api.moonshot.cn/v1",
        "docs_url": "https://platform.moonshot.cn/console/api-keys",
        "env_var": "MOONSHOT_API_KEY",
    },
    "google": {
        "label": "Google (Gemini)",
        "default_model": "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "docs_url": "https://aistudio.google.com/apikey",
        "env_var": "GEMINI_API_KEY",
    },
    "custom": {
        "label": "Custom (OpenAI-compatible)",
        "default_model": "gpt-4o",
        "base_url": "",
        "docs_url": "",
        "env_var": "CUSTOM_API_KEY",
    },
}


class SetAIConfigBody(BaseModel):
    provider: str
    api_key: str
    model: str | None = None
    base_url: str | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str | None) -> str | None:
        if not v:
            return v
        from urllib.parse import urlparse
        import ipaddress
        parsed = urlparse(v)
        host = parsed.hostname
        if host:
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValueError("base_url must not point to a private or internal IP")
            except ValueError:
                pass
        return v


class UpdateAIModelBody(BaseModel):
    model: str


@router.get("/presets")
async def list_presets():
    return PROVIDER_PRESETS


@router.get("/config")
async def get_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserAIConfig).where(UserAIConfig.user_id == user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"configured": False, "provider": None, "model": None, "has_key": False}
    return {
        "configured": True,
        "provider": config.provider,
        "model": config.model,
        "base_url": config.base_url,
        "has_key": True,
    }


@router.put("/config")
async def set_config(
    body: SetAIConfigBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.provider not in PROVIDER_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")

    preset = PROVIDER_PRESETS[body.provider]
    model = body.model or preset["default_model"]
    base_url = body.base_url or preset.get("base_url", "")

    result = await db.execute(
        select(UserAIConfig).where(UserAIConfig.user_id == user.id)
    )
    config = result.scalar_one_or_none()

    if config:
        config.provider = body.provider
        config.encrypted_api_key = encrypt(body.api_key)
        config.model = model
        config.base_url = base_url
    else:
        config = UserAIConfig(
            user_id=user.id,
            provider=body.provider,
            encrypted_api_key=encrypt(body.api_key),
            model=model,
            base_url=base_url,
        )
        db.add(config)

    await db.commit()
    return {"configured": True, "provider": body.provider, "model": model}


@router.patch("/config/model")
async def update_model(
    body: UpdateAIModelBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserAIConfig).where(UserAIConfig.user_id == user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="No AI config found. Set up your API key first.")

    config.model = body.model
    await db.commit()
    return {"provider": config.provider, "model": config.model}


@router.delete("/config")
async def delete_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserAIConfig).where(UserAIConfig.user_id == user.id)
    )
    config = result.scalar_one_or_none()
    if config:
        await db.delete(config)
        await db.commit()
    return {"configured": False}

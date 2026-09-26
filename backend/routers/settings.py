from typing import Literal, Optional

import anthropic
import openai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import get_settings, save_env_values
from backend.services.ai_service import openai_compatible_client

router = APIRouter()


def _key_hint(key: str) -> Optional[str]:
    return f"…{key[-4:]}" if len(key) >= 8 else None


def _settings_status() -> dict:
    # Never return API keys to the renderer — only whether one is set
    s = get_settings()
    compat_configured = bool(s.openai_compat_base_url and s.openai_compat_model)
    return {
        "ai_provider": s.ai_provider,
        "ai_configured": compat_configured
        if s.ai_provider == "openai_compatible"
        else bool(s.anthropic_api_key),
        "anthropic_api_key_set": bool(s.anthropic_api_key),
        "anthropic_api_key_hint": _key_hint(s.anthropic_api_key),
        "openai_compat": {
            "base_url": s.openai_compat_base_url,
            "model": s.openai_compat_model,
            "api_key_set": bool(s.openai_compat_api_key),
            "api_key_hint": _key_hint(s.openai_compat_api_key),
        },
    }


@router.get("")
async def get_app_settings():
    return _settings_status()


class ProviderRequest(BaseModel):
    provider: Literal["anthropic", "openai_compatible"]


@router.put("/ai-provider")
async def set_ai_provider(req: ProviderRequest):
    save_env_values({"AI_PROVIDER": req.provider})
    return _settings_status()


class ApiKeyRequest(BaseModel):
    api_key: str


@router.put("/anthropic-api-key")
async def set_anthropic_api_key(req: ApiKeyRequest):
    api_key = req.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=422, detail="API key is empty")

    # Verify the key before saving it; listing models costs no tokens
    client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=1, timeout=15.0)
    try:
        await client.models.list(limit=1)
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=400, detail="Anthropic rejected this API key")
    except anthropic.PermissionDeniedError:
        raise HTTPException(status_code=400, detail="This API key lacks the required permissions")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="Couldn't reach Anthropic to verify the key")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"Anthropic returned an error ({e.status_code})")
    finally:
        await client.close()

    save_env_values({"ANTHROPIC_API_KEY": api_key})
    return _settings_status()


class OpenAICompatRequest(BaseModel):
    base_url: str
    model: str
    # None keeps the saved key; "" clears it (local servers need none)
    api_key: Optional[str] = None


@router.put("/openai-compatible")
async def set_openai_compatible(req: OpenAICompatRequest):
    base_url = req.base_url.strip().rstrip("/")
    model = req.model.strip()
    if not base_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="Base URL must start with http:// or https://")
    if not model:
        raise HTTPException(status_code=422, detail="Model is empty")
    api_key = get_settings().openai_compat_api_key if req.api_key is None else req.api_key.strip()

    # Verify the endpoint and model by listing models (no tokens spent). This
    # catches wrong URLs, rejected keys and unknown model IDs. Some providers
    # (e.g. OpenRouter) list models without checking the key, so a bad key
    # there only shows up on the first chat message.
    client = openai_compatible_client(base_url, api_key)
    try:
        model_ids = {m.id async for m in client.with_options(max_retries=1, timeout=15.0).models.list()}
    except openai.AuthenticationError:
        raise HTTPException(status_code=400, detail="The provider rejected this API key")
    except openai.PermissionDeniedError:
        raise HTTPException(status_code=400, detail="This API key lacks the required permissions")
    except openai.NotFoundError:
        model_ids = None  # endpoint has no /models; can't verify the model ID
    except openai.APIConnectionError:
        raise HTTPException(status_code=400, detail=f"Couldn't reach {base_url}")
    except openai.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"The provider returned an error ({e.status_code})")
    finally:
        await client.close()

    if model_ids is not None and model not in model_ids:
        raise HTTPException(status_code=400, detail=f"Model '{model}' isn't available at {base_url}")

    save_env_values(
        {
            "OPENAI_COMPAT_BASE_URL": base_url,
            "OPENAI_COMPAT_MODEL": model,
            "OPENAI_COMPAT_API_KEY": api_key,
        }
    )
    return _settings_status()

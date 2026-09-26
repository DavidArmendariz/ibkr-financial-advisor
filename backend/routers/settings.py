import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import get_settings, save_anthropic_api_key

router = APIRouter()


def _settings_status() -> dict:
    # Never return the key itself to the renderer — only whether one is set
    key = get_settings().anthropic_api_key
    return {
        "anthropic_api_key_set": bool(key),
        "anthropic_api_key_hint": f"…{key[-4:]}" if len(key) >= 8 else None,
    }


@router.get("")
async def get_app_settings():
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

    save_anthropic_api_key(api_key)
    return _settings_status()

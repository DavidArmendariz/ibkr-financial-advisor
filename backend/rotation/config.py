from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config import ENV_FILE, save_env_values


class RotationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="ROTATION_", extra="ignore")

    timeframe: Literal["weekly", "daily"] = "weekly"
    tail: int = Field(8, ge=3, le=20)


@lru_cache
def get_rotation_settings() -> RotationSettings:
    return RotationSettings()


def save_rotation_settings(values: dict) -> RotationSettings:
    # Validate the merged result first, so a bad value never reaches .env.
    merged = RotationSettings.model_validate({**get_rotation_settings().model_dump(), **values})
    save_env_values({f"ROTATION_{key.upper()}": str(getattr(merged, key)) for key in values})
    get_rotation_settings.cache_clear()
    return get_rotation_settings()

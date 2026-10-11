from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config import ENV_FILE, save_env_values


class GammaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="GAMMA_", extra="ignore")

    symbol: str = "SOXL"
    max_days: int = Field(45, ge=1, le=365)
    strike_range_pct: float = Field(25.0, ge=5, le=100)
    refresh_minutes: int = Field(15, ge=1, le=240)
    risk_free_rate: float = Field(0.04, ge=0, le=0.2)


@lru_cache
def get_gamma_settings() -> GammaSettings:
    return GammaSettings()


def save_gamma_settings(values: dict) -> GammaSettings:
    validated = GammaSettings.model_validate(get_gamma_settings().model_dump() | values)
    save_env_values({f"GAMMA_{k.upper()}": str(v) for k, v in validated.model_dump().items() if k in values})
    get_gamma_settings.cache_clear()
    return get_gamma_settings()

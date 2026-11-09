from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config import ENV_FILE, save_env_values


class TradingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="TRADING_", extra="ignore")

    live_enabled: bool = False
    max_order_value: float = Field(25_000.0, gt=0, le=10_000_000)
    gap_cap_percent: float = Field(1.0, gt=0, le=10)


@lru_cache
def get_trading_settings() -> TradingSettings:
    return TradingSettings()


def save_trading_settings(values: dict) -> TradingSettings:
    # Validate the merged result first, so a bad value never reaches .env.
    merged = TradingSettings.model_validate({**get_trading_settings().model_dump(), **values})
    save_env_values({f"TRADING_{key.upper()}": str(getattr(merged, key)).lower() if isinstance(getattr(merged, key), bool) else str(getattr(merged, key)) for key in values})
    get_trading_settings.cache_clear()
    return get_trading_settings()

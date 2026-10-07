from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config import ENV_FILE, save_env_values

ALLOWED_TIMEFRAMES = (1, 2, 3, 5, 10, 15, 30)


class SignalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="SIGNALS_", extra="ignore")

    symbol: str = "SOXL"
    timeframe_minutes: int = Field(1, ge=1, le=30)
    ema_fast: int = Field(9, ge=2, le=200)
    ema_slow: int = Field(21, ge=3, le=400)
    bb_period: int = Field(20, ge=2, le=200)
    bb_std: float = Field(2.0, gt=0, le=5)
    rvol_period: int = Field(20, ge=2, le=200)
    rvol_threshold: float = Field(1.5, ge=0, le=20)
    include_premarket: bool = False
    open_blackout_minutes: int = Field(10, ge=0, le=120)
    close_blackout_minutes: int = Field(10, ge=0, le=120)
    cooldown_minutes: int = Field(5, ge=0, le=240)
    llm_enabled: bool = False
    llm_confidence_threshold: float = Field(0.6, ge=0, le=1)
    llm_model_anthropic: str = "claude-haiku-4-5-20251001"
    llm_model_openai: str = "gpt-4.1-mini"
    llm_model_openrouter: str = "anthropic/claude-haiku-4.5"

    def warmup_bars(self) -> int:
        # EMAs need a few periods to forget their seed value.
        return max(3 * self.ema_slow, 3 * self.ema_fast, self.bb_period, self.rvol_period) + 1

    def pipeline_key(self) -> tuple:
        # Changing any of these invalidates indicator state, so the stream re-warms.
        return (
            self.symbol,
            self.timeframe_minutes,
            self.ema_fast,
            self.ema_slow,
            self.bb_period,
            self.bb_std,
            self.rvol_period,
            self.include_premarket,
        )


@lru_cache
def get_signal_settings() -> SignalSettings:
    return SignalSettings()


def save_signal_settings(values: dict) -> SignalSettings:
    merged = get_signal_settings().model_dump() | values
    validated = SignalSettings.model_validate(merged)
    if validated.timeframe_minutes not in ALLOWED_TIMEFRAMES:
        raise ValueError(f"timeframe_minutes must be one of {ALLOWED_TIMEFRAMES}")
    if validated.ema_fast >= validated.ema_slow:
        raise ValueError("ema_fast must be shorter than ema_slow")
    save_env_values(
        {
            f"SIGNALS_{key.upper()}": str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in validated.model_dump().items()
            if key in values
        }
    )
    get_signal_settings.cache_clear()
    return get_signal_settings()

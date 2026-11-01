from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config import ENV_FILE, save_env_values

DEFAULT_SYMBOLS = "NVDA,TSM,AVGO,AMD,ASML,MU,INTC,QCOM,AMAT,LRCX"


class CalendarSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="CALENDAR_", extra="ignore")

    fred_api_key: str = ""
    finnhub_api_key: str = ""
    earnings_symbols: str = DEFAULT_SYMBOLS
    alert_evening_enabled: bool = True
    alert_soon_enabled: bool = True

    def symbols(self) -> list[str]:
        return [s for s in dict.fromkeys(p.strip().upper() for p in self.earnings_symbols.split(",")) if s]


def hint(key: str) -> str | None:
    return f"…{key[-4:]}" if len(key) >= 8 else None


def public_settings(s: CalendarSettings) -> dict:
    return {
        "fred_key_set": bool(s.fred_api_key),
        "fred_key_hint": hint(s.fred_api_key),
        "finnhub_key_set": bool(s.finnhub_api_key),
        "finnhub_key_hint": hint(s.finnhub_api_key),
        "earnings_symbols": s.symbols(),
        "alert_evening_enabled": s.alert_evening_enabled,
        "alert_soon_enabled": s.alert_soon_enabled,
    }


@lru_cache
def get_calendar_settings() -> CalendarSettings:
    return CalendarSettings()


def save_calendar_settings(values: dict) -> CalendarSettings:
    env = {
        f"CALENDAR_{key.upper()}": str(value).lower() if isinstance(value, bool) else str(value)
        for key, value in values.items()
    }
    save_env_values(env)
    get_calendar_settings.cache_clear()
    return get_calendar_settings()

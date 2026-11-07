from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config import ENV_FILE, save_env_values


class PlannerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="PLANNER_", extra="ignore")

    symbol: Literal["SOXL", "SOXS"] = "SOXL"
    atr_basis: Literal["intraday", "daily"] = "intraday"
    stop_multiple: float = Field(1.5, gt=0, le=20)
    target_multiple: float = Field(3.0, gt=0, le=50)
    risk_mode: Literal["percent", "dollars"] = "percent"
    risk_percent: float = Field(1.0, gt=0, le=100)
    risk_dollars: float = Field(1000.0, gt=0, le=10_000_000)


@lru_cache
def get_planner_settings() -> PlannerSettings:
    return PlannerSettings()


def save_planner_settings(values: dict) -> PlannerSettings:
    # Validate the merged result first, so a bad value never reaches .env.
    merged = PlannerSettings.model_validate({**get_planner_settings().model_dump(), **values})
    save_env_values({f"PLANNER_{key.upper()}": str(getattr(merged, key)) for key in values})
    get_planner_settings.cache_clear()
    return get_planner_settings()

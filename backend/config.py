import os
from functools import lru_cache
from pathlib import Path

from dotenv import set_key
from pydantic_settings import BaseSettings, SettingsConfigDict

# Relative to the backend's working directory: the repo root in dev, the
# per-user data dir (~/Library/Application Support/<app>) when packaged.
ENV_FILE = Path(".env")


class Settings(BaseSettings):
    # "anthropic" or "openai_compatible" (OpenRouter, OpenAI, Ollama, LM Studio, …)
    ai_provider: str = "anthropic"
    anthropic_api_key: str = ""
    # Deliberately not OPENAI_*: the openai SDK and users' shells use those names
    # for OpenAI itself, which would silently leak into an OpenRouter/Ollama setup.
    openai_compat_base_url: str = "https://openrouter.ai/api/v1"
    openai_compat_api_key: str = ""
    openai_compat_model: str = ""
    ibkr_host: str = "127.0.0.1"
    ibkr_paper_port: int = 7497
    ibkr_live_port: int = 7496
    ibkr_client_id: int = 1
    backend_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./ibkr_advisor.db"

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def save_env_values(values: dict[str, str]) -> None:
    """Persist settings to .env (owner-only permissions) and apply them immediately."""
    ENV_FILE.touch(mode=0o600, exist_ok=True)
    for key, value in values.items():
        set_key(ENV_FILE, key, value, quote_mode="never")
        # Process env vars take precedence over .env in pydantic-settings, so
        # update them too — otherwise a value exported in the shell would
        # shadow the saved one.
        os.environ[key] = value
    ENV_FILE.chmod(0o600)
    get_settings.cache_clear()

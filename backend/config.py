import os
from functools import lru_cache
from pathlib import Path

from dotenv import set_key
from pydantic_settings import BaseSettings, SettingsConfigDict

# Relative to the backend's working directory: the repo root in dev, the
# per-user data dir (~/Library/Application Support/<app>) when packaged.
ENV_FILE = Path(".env")


class Settings(BaseSettings):
    anthropic_api_key: str = ""
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


def save_anthropic_api_key(api_key: str) -> None:
    """Persist the key to .env (owner-only permissions) and apply it immediately."""
    ENV_FILE.touch(mode=0o600, exist_ok=True)
    set_key(ENV_FILE, "ANTHROPIC_API_KEY", api_key, quote_mode="never")
    ENV_FILE.chmod(0o600)
    # Process env vars take precedence over .env in pydantic-settings, so update
    # it too — otherwise a key exported in the shell would shadow the saved one.
    os.environ["ANTHROPIC_API_KEY"] = api_key
    get_settings.cache_clear()

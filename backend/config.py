from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    ibkr_host: str = "127.0.0.1"
    ibkr_paper_port: int = 7497
    ibkr_live_port: int = 7496
    ibkr_client_id: int = 1
    backend_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./ibkr_advisor.db"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()

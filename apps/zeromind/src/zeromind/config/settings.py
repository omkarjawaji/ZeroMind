"""Read-plane settings (executor keeps its own settings and secrets, ADR-0002)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZEROMIND_", env_file=".env", extra="ignore")

    db_path: Path = Path("data/zeromind.db")
    qdrant_url: str = "http://localhost:6333"
    kite_proxy_url: str | None = None

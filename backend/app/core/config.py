from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Nexus API"
    version: str = "0.1.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = "postgresql+asyncpg://nexus:nexus_dev_pw@localhost:5432/nexus"
    database_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    password_time_cost: int = 3
    password_memory_cost: int = 65536
    password_parallelism: int = 4
    password_hash_len: int = 32
    password_salt_len: int = 16
    password_max_length: int = 128

    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7

    storage_root: Path = Path("./var/documents")
    storage_max_file_size_bytes: int = 100 * 1024 * 1024

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "+psycopg", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

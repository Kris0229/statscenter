from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/statscenter",
    )
    JWT_SECRET: str = Field(default="dev-secret-change-me")
    JWT_ACCESS_TTL: int = 900
    JWT_REFRESH_TTL: int = 1_209_600
    CORS_ORIGINS: str = "*"

    STORAGE_BACKEND: str = "local"
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_KEY: str | None = None

    SUPERADMIN_EMAIL: str | None = None
    SUPERADMIN_PASSWORD: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if raw == "*" or not raw:
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

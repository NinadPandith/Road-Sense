"""Application settings, read from environment variables (see .env.example)."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_name: str = "RoadSense API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/roadsense"
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""

    hf_model_repo: str = ""
    model_version: str = "dev"
    detector_file: str = "yolo-small.onnx"
    depth_file: str = "depth-anything-v2-small.onnx"
    model_cache_dir: str = ".model_cache"

    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    cron_secret: str = "change-me"
    ip_hash_salt: str = "change-me"
    pilot_area_path: str = ""

    max_upload_mb: int = 50
    rate_limit_per_hour: int = 10
    sentry_dsn: str = ""

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        if isinstance(v, str) and not v.startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()

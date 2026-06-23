from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    default_dry_run: bool = True
    max_offers_per_run: int = 5
    enable_real_publish: bool = False

    shopee_partner_id: str | None = None
    shopee_secret_key: str | None = None
    shopee_tracking_id: str | None = None

    amazon_access_key: str | None = None
    amazon_secret_key: str | None = None
    amazon_partner_tag: str | None = None
    amazon_region: str = "BR"


def get_settings() -> Settings:
    return Settings()

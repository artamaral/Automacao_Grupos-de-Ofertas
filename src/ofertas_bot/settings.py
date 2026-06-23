from __future__ import annotations

from os import getenv
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    default_dry_run: bool = True
    max_offers_per_run: int = 5
    enable_real_publish: bool = False
    enable_real_http: bool = False

    shopee_partner_id: str | None = None
    shopee_secret_key: str | None = None
    shopee_tracking_id: str | None = None

    amazon_access_key: str | None = None
    amazon_secret_key: str | None = None
    amazon_partner_tag: str | None = None
    amazon_region: str = "BR"

    def __init__(self, **values: Any) -> None:
        if "_env_file" not in values and _running_under_pytest():
            values["_env_file"] = None
        super().__init__(**values)


def get_settings() -> Settings:
    return Settings()


def _running_under_pytest() -> bool:
    return bool(getenv("PYTEST_CURRENT_TEST"))

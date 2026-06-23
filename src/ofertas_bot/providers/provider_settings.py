from __future__ import annotations

from dataclasses import dataclass
from os import getenv


DEFAULT_PROVIDER_BASE_URL = "https://example.com"


@dataclass(frozen=True)
class ProviderBaseUrls:
    shopee: str = DEFAULT_PROVIDER_BASE_URL
    amazon: str = DEFAULT_PROVIDER_BASE_URL


def get_provider_base_urls() -> ProviderBaseUrls:
    return ProviderBaseUrls(
        shopee=getenv("SHOPEE_BASE_URL", DEFAULT_PROVIDER_BASE_URL),
        amazon=getenv("AMAZON_BASE_URL", DEFAULT_PROVIDER_BASE_URL),
    )

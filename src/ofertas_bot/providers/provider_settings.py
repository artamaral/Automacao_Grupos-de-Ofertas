from __future__ import annotations

from dataclasses import dataclass
from os import getenv

from ofertas_bot.providers.endpoints import AMAZON_SEARCH_PATH, SHOPEE_SEARCH_PATH

DEFAULT_PROVIDER_BASE_URL = "https://example.com"
TRUE_ENV_VALUES = {"1", "true", "yes", "sim"}


@dataclass(frozen=True)
class ProviderBaseUrls:
    shopee: str = DEFAULT_PROVIDER_BASE_URL
    amazon: str = DEFAULT_PROVIDER_BASE_URL


@dataclass(frozen=True)
class ProviderPaths:
    shopee_search: str = SHOPEE_SEARCH_PATH
    amazon_search: str = AMAZON_SEARCH_PATH


@dataclass(frozen=True)
class ProviderPathConfirmations:
    shopee_search: bool = False


def get_provider_base_urls() -> ProviderBaseUrls:
    return ProviderBaseUrls(
        shopee=getenv("SHOPEE_BASE_URL", DEFAULT_PROVIDER_BASE_URL),
        amazon=getenv("AMAZON_BASE_URL", DEFAULT_PROVIDER_BASE_URL),
    )


def get_provider_paths() -> ProviderPaths:
    return ProviderPaths(
        shopee_search=getenv("SHOPEE_SEARCH_PATH", SHOPEE_SEARCH_PATH),
        amazon_search=getenv("AMAZON_SEARCH_PATH", AMAZON_SEARCH_PATH),
    )


def get_provider_path_confirmations() -> ProviderPathConfirmations:
    return ProviderPathConfirmations(
        shopee_search=_env_flag_is_true("SHOPEE_SEARCH_PATH_CONFIRMED"),
    )


def _env_flag_is_true(name: str) -> bool:
    value = getenv(name, "")
    return value.strip().lower() in TRUE_ENV_VALUES

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from ofertas_bot.providers.provider_settings import DEFAULT_PROVIDER_BASE_URL


class RealHttpValidationError(RuntimeError):
    """Raised when a real HTTP call is not explicitly safe to run."""


@dataclass(frozen=True)
class RealHttpPrerequisites:
    provider_name: str
    enabled: bool
    base_url: str
    required_config: dict[str, object | None]


def validate_real_http_prerequisites(prerequisites: RealHttpPrerequisites) -> None:
    missing_items: list[str] = []

    if not prerequisites.enabled:
        missing_items.append("real HTTP flag enabled")

    if not _is_valid_https_url(prerequisites.base_url):
        missing_items.append("valid HTTPS base URL")

    if prerequisites.base_url == DEFAULT_PROVIDER_BASE_URL:
        missing_items.append("non-placeholder base URL")

    missing_items.extend(
        label for label, value in prerequisites.required_config.items() if not _has_value(value)
    )

    if missing_items:
        joined_items = ", ".join(missing_items)
        msg = f"Real HTTP for {prerequisites.provider_name} is blocked: {joined_items}"
        raise RealHttpValidationError(msg)


def _is_valid_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _has_value(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True

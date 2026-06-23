from __future__ import annotations

from typing import Any

MASK = "<redacted>"
REDACTED_URL = "https://example.com/redacted"
REDACTED_TITLE = "Produto anonimizado"

SENSITIVE_KEY_PARTS = (
    "auth",
    "cookie",
    "credential",
    "email",
    "phone",
    "secret",
    "session",
    "sign",
    "token",
)
URL_KEY_PARTS = ("url", "link", "image")
TITLE_KEYS = {"title", "item_name", "product_name", "name"}
SELLER_KEY_PARTS = ("seller", "shop", "user")


def anonymize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _anonymize_field(key=key, value=item) for key, item in value.items()}
    if isinstance(value, list):
        return [anonymize_payload(item) for item in value]
    return value


def _anonymize_field(key: str, value: Any) -> Any:
    normalized_key = key.lower()

    if _is_sensitive_key(normalized_key):
        return MASK

    if _is_url_key(normalized_key) and isinstance(value, str):
        return REDACTED_URL

    if normalized_key in TITLE_KEYS and isinstance(value, str):
        return REDACTED_TITLE

    if _is_seller_identity_key(normalized_key):
        return MASK

    return anonymize_payload(value)


def _is_sensitive_key(normalized_key: str) -> bool:
    return any(part in normalized_key for part in SENSITIVE_KEY_PARTS)


def _is_url_key(normalized_key: str) -> bool:
    return any(part in normalized_key for part in URL_KEY_PARTS)


def _is_seller_identity_key(normalized_key: str) -> bool:
    if not any(part in normalized_key for part in SELLER_KEY_PARTS):
        return False
    return normalized_key.endswith("id") or normalized_key.endswith("name")

import json
from pathlib import Path
from typing import Any

ALLOWED_REDACTED_URL = "https://example.com/redacted"
MASK = "<redacted>"
FIXTURE_GLOB = "*anonymized*.json"
FIXTURE_ROOT = Path("tests/fixtures")
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


def test_anonymized_fixtures_do_not_expose_sensitive_values() -> None:
    fixture_paths = sorted(FIXTURE_ROOT.glob(FIXTURE_GLOB))

    assert fixture_paths, "expected at least one anonymized fixture"

    for fixture_path in fixture_paths:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        failures = list(_find_safety_failures(payload))
        assert not failures, f"{fixture_path} has unsafe values: {failures}"


def _find_safety_failures(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = key.lower()
            item_path = f"{path}.{key}"

            if _is_sensitive_key(normalized_key) and item != MASK:
                yield f"{item_path} must be redacted"
                continue

            if _is_url_key(normalized_key) and isinstance(item, str) and item != ALLOWED_REDACTED_URL:
                yield f"{item_path} must use redacted URL"
                continue

            if normalized_key in TITLE_KEYS and isinstance(item, str) and item != REDACTED_TITLE:
                yield f"{item_path} must use anonymized title"
                continue

            if _is_seller_identity_key(normalized_key) and item != MASK:
                yield f"{item_path} must be redacted"
                continue

            yield from _find_safety_failures(item, item_path)

    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _find_safety_failures(item, f"{path}[{index}]")


def _is_sensitive_key(normalized_key: str) -> bool:
    return any(part in normalized_key for part in SENSITIVE_KEY_PARTS)


def _is_url_key(normalized_key: str) -> bool:
    return any(part in normalized_key for part in URL_KEY_PARTS)


def _is_seller_identity_key(normalized_key: str) -> bool:
    if not any(part in normalized_key for part in SELLER_KEY_PARTS):
        return False
    return normalized_key.endswith("id") or normalized_key.endswith("name")

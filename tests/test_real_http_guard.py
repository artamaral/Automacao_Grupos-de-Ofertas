import pytest

from ofertas_bot.providers.provider_settings import DEFAULT_PROVIDER_BASE_URL
from ofertas_bot.providers.real_http_guard import (
    RealHttpPrerequisites,
    RealHttpValidationError,
    validate_real_http_prerequisites,
)


def make_prerequisites(**overrides) -> RealHttpPrerequisites:
    values = {
        "provider_name": "Provider Teste",
        "enabled": True,
        "base_url": "https://api.example.test",
        "required_config": {"account id": "123", "tracking id": "abc"},
    }
    values.update(overrides)
    return RealHttpPrerequisites(**values)


def test_real_http_guard_allows_valid_prerequisites() -> None:
    validate_real_http_prerequisites(make_prerequisites())


def test_real_http_guard_blocks_when_flag_is_disabled() -> None:
    with pytest.raises(RealHttpValidationError, match="real HTTP flag enabled"):
        validate_real_http_prerequisites(make_prerequisites(enabled=False))


def test_real_http_guard_blocks_placeholder_base_url() -> None:
    with pytest.raises(RealHttpValidationError, match="non-placeholder base URL"):
        validate_real_http_prerequisites(
            make_prerequisites(base_url=DEFAULT_PROVIDER_BASE_URL)
        )


def test_real_http_guard_blocks_non_https_base_url() -> None:
    with pytest.raises(RealHttpValidationError, match="valid HTTPS base URL"):
        validate_real_http_prerequisites(make_prerequisites(base_url="http://api.test"))


def test_real_http_guard_blocks_missing_required_config() -> None:
    with pytest.raises(RealHttpValidationError, match="tracking id"):
        validate_real_http_prerequisites(
            make_prerequisites(required_config={"account id": "123", "tracking id": ""})
        )


def test_real_http_guard_reports_provider_name() -> None:
    with pytest.raises(RealHttpValidationError, match="Provider Teste"):
        validate_real_http_prerequisites(make_prerequisites(enabled=False))

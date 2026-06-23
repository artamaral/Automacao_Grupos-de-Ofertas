from ofertas_bot.providers.endpoints import AMAZON_SEARCH_PATH, SHOPEE_SEARCH_PATH
from ofertas_bot.providers.provider_settings import (
    get_provider_path_confirmations,
    get_provider_paths,
)


def test_provider_paths_use_safe_defaults(monkeypatch) -> None:
    monkeypatch.delenv("SHOPEE_SEARCH_PATH", raising=False)
    monkeypatch.delenv("AMAZON_SEARCH_PATH", raising=False)

    paths = get_provider_paths()

    assert paths.shopee_search == SHOPEE_SEARCH_PATH
    assert paths.amazon_search == AMAZON_SEARCH_PATH


def test_provider_paths_can_be_configured_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_SEARCH_PATH", "/custom/shopee/search")
    monkeypatch.setenv("AMAZON_SEARCH_PATH", "/custom/amazon/search")

    paths = get_provider_paths()

    assert paths.shopee_search == "/custom/shopee/search"
    assert paths.amazon_search == "/custom/amazon/search"


def test_provider_path_confirmations_default_to_false(monkeypatch) -> None:
    monkeypatch.delenv("SHOPEE_SEARCH_PATH_CONFIRMED", raising=False)

    confirmations = get_provider_path_confirmations()

    assert confirmations.shopee_search is False


def test_provider_path_confirmations_accept_truthy_values(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_SEARCH_PATH_CONFIRMED", "true")

    confirmations = get_provider_path_confirmations()

    assert confirmations.shopee_search is True

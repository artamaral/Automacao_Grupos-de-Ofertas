from ofertas_bot.providers.amazon import AmazonProvider
from ofertas_bot.providers.provider_settings import (
    get_provider_base_urls,
    get_provider_graphql_urls,
)
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.settings import Settings


def test_provider_base_urls_use_safe_defaults(monkeypatch) -> None:
    monkeypatch.delenv("SHOPEE_BASE_URL", raising=False)
    monkeypatch.delenv("AMAZON_BASE_URL", raising=False)

    base_urls = get_provider_base_urls()

    assert base_urls.shopee == "https://example.com"
    assert base_urls.amazon == "https://example.com"


def test_provider_base_urls_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_BASE_URL", "https://shopee.example.test")
    monkeypatch.setenv("AMAZON_BASE_URL", "https://amazon.example.test")

    base_urls = get_provider_base_urls()

    assert base_urls.shopee == "https://shopee.example.test"
    assert base_urls.amazon == "https://amazon.example.test"


def test_shopee_provider_uses_configured_graphql_url(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://shopee.example.test/graphql")
    provider = ShopeeProvider(
        settings=Settings(shopee_partner_id="partner", shopee_secret_key="credential")
    )

    request = provider.build_search_request(
        keyword="maquiagem",
        limit=1,
        timestamp=1700000000,
    )

    assert request.url == "https://shopee.example.test/graphql"


def test_provider_graphql_urls_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://shopee.example.test/graphql")

    urls = get_provider_graphql_urls()

    assert urls.shopee == "https://shopee.example.test/graphql"


def test_amazon_provider_uses_configured_base_url(monkeypatch) -> None:
    monkeypatch.setenv("AMAZON_BASE_URL", "https://amazon.example.test")
    provider = AmazonProvider(
        settings=Settings(
            amazon_access_key="access",
            amazon_secret_key="credential",
            amazon_partner_tag="tag-20",
        )
    )

    request = provider._get_gateway().build_search_request(keyword="casa", limit=1)

    assert request.url.startswith("https://amazon.example.test")

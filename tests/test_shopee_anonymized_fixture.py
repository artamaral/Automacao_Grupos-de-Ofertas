import json
from pathlib import Path

from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.settings import Settings

FIXTURE_PATH = Path("tests/fixtures/shopee-real-anonymized.example.json")


def test_shopee_provider_normalizes_anonymized_fixture() -> None:
    response_data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    provider = ShopeeProvider(
        settings=Settings(
            shopee_partner_id="partner",
            shopee_secret_key="credential",
        )
    )

    offers = provider.normalize_response(
        response_data=response_data,
        niche="maquiagem",
        limit=1,
    )

    assert len(offers) == 1
    assert offers[0].title == "Produto anonimizado"
    assert offers[0].url == "https://example.com/redacted"
    assert offers[0].price == 0
    assert offers[0].old_price is None
    assert offers[0].commission_rate == 0.08
    assert offers[0].sales_count == 0
    assert offers[0].rating is None
    assert offers[0].niche == "maquiagem"
    assert offers[0].is_prime_or_free_shipping is False

from ofertas_bot.providers.amazon_request import AmazonSearchRequestBuilder
from ofertas_bot.providers.endpoints import AMAZON_SEARCH_PATH


def test_amazon_search_request_builder_creates_http_request() -> None:
    builder = AmazonSearchRequestBuilder(
        partner_tag="tag-20",
        base_url="https://example.com",
    )

    request = builder.build(keyword="maquiagem", limit=10)

    assert request.method == "POST"
    assert request.url == f"https://example.com{AMAZON_SEARCH_PATH}"
    assert request.body is not None
    assert request.body["Keywords"] == "maquiagem"
    assert request.body["PartnerTag"] == "tag-20"
    assert request.body["PartnerType"] == "Associates"
    assert request.body["ItemCount"] == 10
    assert "Offers.Listings.Price" in request.body["Resources"]

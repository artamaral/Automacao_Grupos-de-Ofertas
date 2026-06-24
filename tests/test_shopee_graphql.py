import pytest

from ofertas_bot.providers.shopee_graphql import (
    SHOPEE_GENERATE_SHORT_LINK_OPERATION,
    SHOPEE_OFFER_LIST_OPERATION,
    ShopeeGraphqlAuthorization,
    ShopeeGraphqlPayloadError,
    ShopeeGraphqlSigner,
    ShopeeOfferListGraphqlRequestBuilder,
    ShopeeShortLinkGraphqlRequestBuilder,
    encode_graphql_payload,
    extract_shopee_offer_connection,
    extract_shopee_short_link,
    raise_if_graphql_errors,
)


def make_signer() -> ShopeeGraphqlSigner:
    return ShopeeGraphqlSigner(
        credential="credential",
        api_secret="secret",
    )


def test_shopee_graphql_authorization_formats_header() -> None:
    auth = ShopeeGraphqlAuthorization(
        credential="credential",
        signature="signature",
        timestamp=1577836800,
    )

    assert (
        auth.header_value()
        == "SHA256 Credential=credential, Signature=signature, Timestamp=1577836800"
    )


def test_shopee_graphql_signer_uses_official_signature_factor() -> None:
    payload = (
        '{"query":"{\\nbrandOffer{\\n    nodes{\\n        commissionRate\\n'
        '        offerName\\n    }\\n}\\n}"}'
    )
    signer = ShopeeGraphqlSigner(credential="123456", api_secret="demo")

    auth = signer.sign_payload(payload=payload, timestamp=1577836800)

    assert (
        auth.signature
        == "dc88d72feea70c80c52c3399751a7d34966763f51a7f056aa070a5e9df645412"
    )
    assert (
        auth.header_value()
        == "SHA256 Credential=123456, "
        "Signature=dc88d72feea70c80c52c3399751a7d34966763f51a7f056aa070a5e9df645412, "
        "Timestamp=1577836800"
    )


def test_encode_graphql_payload_uses_compact_json() -> None:
    payload = encode_graphql_payload({"query": "{ x }", "variables": {"page": 1}})

    assert payload == '{"query":"{ x }","variables":{"page":1}}'


def test_shopee_offer_list_builder_uses_post_json_graphql_request() -> None:
    request = ShopeeOfferListGraphqlRequestBuilder(
        signer=make_signer(),
        timestamp=1577836800,
    ).build(
        keyword="roupa",
        sort_type=2,
        page=1,
        limit=10,
    )

    assert request.method == "POST"
    assert request.url == "https://open-api.affiliate.shopee.com.br/graphql"
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["Authorization"].startswith("SHA256 Credential=credential")
    assert "Signature=" in request.headers["Authorization"]
    assert "Timestamp=1577836800" in request.headers["Authorization"]
    assert request.body is not None
    assert request.body["operationName"] == SHOPEE_OFFER_LIST_OPERATION
    assert "shopeeOfferV2" in request.body["query"]
    assert request.body["variables"] == {
        "keyword": "roupa",
        "sortType": 2,
        "page": 1,
        "limit": 10,
    }


def test_shopee_short_link_builder_uses_post_json_graphql_request() -> None:
    request = ShopeeShortLinkGraphqlRequestBuilder(
        signer=make_signer(),
        timestamp=1577836800,
    ).build(
        origin_url="https://shopee.com.br/produto",
        sub_ids=["grupo-maquiagem", "campanha-1"],
    )

    assert request.method == "POST"
    assert request.body is not None
    assert request.body["operationName"] == SHOPEE_GENERATE_SHORT_LINK_OPERATION
    assert "generateShortLink" in request.body["query"]
    assert request.body["variables"] == {
        "originUrl": "https://shopee.com.br/produto",
        "subIds": ["grupo-maquiagem", "campanha-1"],
    }


def test_extract_shopee_offer_connection_accepts_graphql_response() -> None:
    response_data = {
        "data": {
            "shopeeOfferV2": {
                "nodes": [
                    {
                        "commissionRate": "0.0123",
                        "imageUrl": "https://example.com/image.jpg",
                        "offerLink": "https://s.shopee.com.br/abc",
                        "originalLink": "https://shopee.com.br/produto",
                        "offerName": "Oferta Shopee",
                        "offerType": 1,
                        "collectionId": 123,
                        "periodStartTime": 1577836800,
                        "periodEndTime": 1577923200,
                    }
                ],
                "pageInfo": {
                    "page": 1,
                    "limit": 10,
                    "hasNextPage": True,
                },
            }
        }
    }

    connection = extract_shopee_offer_connection(response_data)

    assert connection["nodes"][0]["offerName"] == "Oferta Shopee"
    assert connection["pageInfo"]["hasNextPage"] is True


def test_extract_shopee_short_link_accepts_graphql_response() -> None:
    response_data = {
        "data": {
            "generateShortLink": {
                "shortLink": "https://s.shopee.com.br/abc",
            }
        }
    }

    assert extract_shopee_short_link(response_data) == "https://s.shopee.com.br/abc"


def test_raise_if_graphql_errors_uses_error_extensions() -> None:
    response_data = {
        "data": {},
        "errors": [
            {
                "message": "Identity authentication error",
                "path": "shopeeOfferV2",
                "extensions": {
                    "code": 10020,
                    "message": "Signature is incorrect or expired",
                },
            }
        ],
    }

    with pytest.raises(ShopeeGraphqlPayloadError, match="code=10020"):
        raise_if_graphql_errors(response_data)

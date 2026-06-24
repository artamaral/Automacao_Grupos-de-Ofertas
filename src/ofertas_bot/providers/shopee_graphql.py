from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from ofertas_bot.providers.endpoints import SHOPEE_GRAPHQL_URL
from ofertas_bot.providers.http import HttpRequest

SHOPEE_OFFER_LIST_OPERATION = "ShopeeOfferList"
SHOPEE_GENERATE_SHORT_LINK_OPERATION = "GenerateShortLink"

SHOPEE_OFFER_LIST_QUERY = """
query ShopeeOfferList($keyword: String, $sortType: Int, $page: Int, $limit: Int) {
  shopeeOfferV2(keyword: $keyword, sortType: $sortType, page: $page, limit: $limit) {
    nodes {
      commissionRate
      imageUrl
      offerLink
      originalLink
      offerName
      offerType
      categoryId
      collectionId
      periodStartTime
      periodEndTime
    }
    pageInfo {
      page
      limit
      hasNextPage
    }
  }
}
""".strip()

SHOPEE_GENERATE_SHORT_LINK_MUTATION = """
mutation GenerateShortLink($originUrl: String, $subIds: [String]) {
  generateShortLink(input: { originUrl: $originUrl, subIds: $subIds }) {
    shortLink
  }
}
""".strip()


class ShopeeGraphqlPayloadError(ValueError):
    """Raised when Shopee GraphQL returns an error envelope or invalid shape."""


@dataclass(frozen=True)
class ShopeeGraphqlAuthorization:
    credential: str
    signature: str
    timestamp: int

    def header_value(self) -> str:
        return (
            "SHA256 "
            f"Credential={self.credential}, "
            f"Signature={self.signature}, "
            f"Timestamp={self.timestamp}"
        )


@dataclass(frozen=True)
class ShopeeGraphqlSigner:
    credential: str
    api_secret: str

    def sign_payload(self, *, payload: str, timestamp: int) -> ShopeeGraphqlAuthorization:
        signature_base = f"{self.credential}{timestamp}{payload}{self.api_secret}"
        signature = hashlib.sha256(signature_base.encode("utf-8")).hexdigest()
        return ShopeeGraphqlAuthorization(
            credential=self.credential,
            signature=signature,
            timestamp=timestamp,
        )


@dataclass(frozen=True)
class ShopeeOfferListGraphqlRequestBuilder:
    signer: ShopeeGraphqlSigner
    timestamp: int
    graphql_url: str = SHOPEE_GRAPHQL_URL

    def build(
        self,
        *,
        keyword: str,
        sort_type: int,
        page: int,
        limit: int,
    ) -> HttpRequest:
        return _build_graphql_request(
            graphql_url=self.graphql_url,
            signer=self.signer,
            timestamp=self.timestamp,
            query=SHOPEE_OFFER_LIST_QUERY,
            operation_name=SHOPEE_OFFER_LIST_OPERATION,
            variables={
                "keyword": keyword,
                "sortType": sort_type,
                "page": page,
                "limit": limit,
            },
        )


@dataclass(frozen=True)
class ShopeeShortLinkGraphqlRequestBuilder:
    signer: ShopeeGraphqlSigner
    timestamp: int
    graphql_url: str = SHOPEE_GRAPHQL_URL

    def build(self, *, origin_url: str, sub_ids: list[str]) -> HttpRequest:
        return _build_graphql_request(
            graphql_url=self.graphql_url,
            signer=self.signer,
            timestamp=self.timestamp,
            query=SHOPEE_GENERATE_SHORT_LINK_MUTATION,
            operation_name=SHOPEE_GENERATE_SHORT_LINK_OPERATION,
            variables={
                "originUrl": origin_url,
                "subIds": sub_ids,
            },
        )


def extract_shopee_offer_connection(response_data: dict[str, Any]) -> dict[str, Any]:
    raise_if_graphql_errors(response_data)

    data = response_data.get("data")
    if not isinstance(data, dict):
        msg = "Shopee GraphQL response field 'data' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    connection = data.get("shopeeOfferV2")
    if not isinstance(connection, dict):
        msg = "Shopee GraphQL response field 'data.shopeeOfferV2' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    nodes = connection.get("nodes")
    if not isinstance(nodes, list):
        msg = "Shopee GraphQL response field 'data.shopeeOfferV2.nodes' must be a list"
        raise ShopeeGraphqlPayloadError(msg)

    page_info = connection.get("pageInfo")
    if not isinstance(page_info, dict):
        msg = "Shopee GraphQL response field 'data.shopeeOfferV2.pageInfo' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    return connection


def extract_shopee_short_link(response_data: dict[str, Any]) -> str:
    raise_if_graphql_errors(response_data)

    data = response_data.get("data")
    if not isinstance(data, dict):
        msg = "Shopee GraphQL response field 'data' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    payload = data.get("generateShortLink")
    if not isinstance(payload, dict):
        msg = "Shopee GraphQL response field 'data.generateShortLink' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    short_link = payload.get("shortLink")
    if not isinstance(short_link, str) or not short_link:
        msg = "Shopee GraphQL response field 'data.generateShortLink.shortLink' must be a string"
        raise ShopeeGraphqlPayloadError(msg)

    return short_link


def raise_if_graphql_errors(response_data: dict[str, Any]) -> None:
    errors = response_data.get("errors")
    if errors is None:
        return
    if not isinstance(errors, list):
        msg = "Shopee GraphQL response field 'errors' must be a list"
        raise ShopeeGraphqlPayloadError(msg)
    if not errors:
        return

    first_error = errors[0]
    if not isinstance(first_error, dict):
        msg = "Shopee GraphQL response contains invalid error item"
        raise ShopeeGraphqlPayloadError(msg)

    message = _optional_text(first_error.get("message")) or "GraphQL error"
    extension_message = _graphql_extension_message(first_error.get("extensions"))
    extension_code = _graphql_extension_code(first_error.get("extensions"))

    details = [message]
    if extension_code is not None:
        details.append(f"code={extension_code}")
    if extension_message:
        details.append(extension_message)

    raise ShopeeGraphqlPayloadError(": ".join(details))


def _build_graphql_request(
    *,
    graphql_url: str,
    signer: ShopeeGraphqlSigner,
    timestamp: int,
    query: str,
    operation_name: str,
    variables: dict[str, Any],
) -> HttpRequest:
    body = {
        "query": query,
        "operationName": operation_name,
        "variables": variables,
    }
    payload = encode_graphql_payload(body)
    authorization = signer.sign_payload(payload=payload, timestamp=timestamp)
    return HttpRequest(
        method="POST",
        url=graphql_url,
        headers={
            "Authorization": authorization.header_value(),
            "Content-Type": "application/json",
        },
        body=body,
    )


def encode_graphql_payload(body: dict[str, Any]) -> str:
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def _graphql_extension_code(extensions: Any) -> int | None:
    if not isinstance(extensions, dict):
        return None
    code = extensions.get("code")
    return code if isinstance(code, int) else None


def _graphql_extension_message(extensions: Any) -> str | None:
    if not isinstance(extensions, dict):
        return None
    return _optional_text(extensions.get("message"))


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None

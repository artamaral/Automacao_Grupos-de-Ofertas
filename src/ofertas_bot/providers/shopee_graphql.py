from __future__ import annotations

import hashlib
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.endpoints import SHOPEE_GRAPHQL_URL
from ofertas_bot.providers.gateway import execute_provider_request, validate_positive_limit
from ofertas_bot.providers.http import HttpRequest, ProviderHttpClient
from ofertas_bot.providers.mapper import ExternalOfferPayload, OfferMapper
from ofertas_bot.providers.retry import RetryPolicy, Sleeper
from ofertas_bot.providers.transport import HttpTransport, encode_json_body

SHOPEE_OFFER_LIST_OPERATION = "ShopeeOfferList"
SHOPEE_PRODUCT_OFFER_LIST_OPERATION = "ProductOfferList"
SHOPEE_GENERATE_SHORT_LINK_OPERATION = "GenerateShortLink"
SHOPEE_SORT_LATEST_DESC = 1
SHOPEE_SORT_HIGHEST_COMMISSION_DESC = 2

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


def build_product_offer_query(
    *,
    list_type: int | None,
    match_id: int | None,
    page: int,
    limit: int,
    keyword: str | None = None,
    sort_type: int | None = None,
    item_id: int | None = None,
    shop_id: int | None = None,
    product_cat_id: int | None = None,
    is_ams_offer: bool | None = None,
    is_key_seller: bool | None = None,
) -> str:
    args = [f"page: {page}", f"limit: {limit}"]
    if list_type is not None:
        args.insert(0, f"listType: {list_type}")
    if match_id is not None:
        args.append(f"matchId: {match_id}")
    if keyword is not None:
        args.append(f'keyword: "{_escape_graphql_string(keyword)}"')
    if sort_type is not None:
        args.append(f"sortType: {sort_type}")
    if item_id is not None:
        args.append(f"itemId: {item_id}")
    if shop_id is not None:
        args.append(f"shopId: {shop_id}")
    if product_cat_id is not None:
        args.append(f"productCatId: {product_cat_id}")
    if is_ams_offer is not None:
        args.append(f"isAMSOffer: {'true' if is_ams_offer else 'false'}")
    if is_key_seller is not None:
        args.append(f"isKeySeller: {'true' if is_key_seller else 'false'}")
    query_args = ", ".join(args)

    return f"""
query {SHOPEE_PRODUCT_OFFER_LIST_OPERATION} {{
  productOfferV2({query_args}) {{
    nodes {{
      itemId
      commissionRate
      appExistRate
      appNewRate
      webExistRate
      webNewRate
      commission
      price
      sales
      shopId
      productName
      imageUrl
      shopName
      productLink
      offerLink
      periodEndTime
      periodStartTime
      priceMin
      priceMax
      productCatIds
      ratingStar
      priceDiscountRate
      shopType
      sellerCommissionRate
      shopeeCommissionRate
    }}
    pageInfo {{
      page
      limit
      hasNextPage
      scrollId
    }}
  }}
}}
""".strip()


class ShopeeGraphqlPayloadError(ValueError):
    """Raised when Shopee GraphQL returns an error envelope or invalid shape."""


class ShopeeGraphqlOfferMapper:
    def __init__(self, marketplace: Marketplace = Marketplace.SHOPEE) -> None:
        self.marketplace = marketplace
        self._mapper = OfferMapper()

    def map_node(self, node: dict[str, Any], niche: str) -> Offer:
        title = (
            _optional_str(node.get("offerName"))
            or _optional_str(node.get("productName"))
            or _optional_str(node.get("shopName"))
            or ""
        )
        payload = ExternalOfferPayload(
            marketplace=self.marketplace,
            title=title,
            url=str(node.get("offerLink", "")),
            image_url=_optional_str(node.get("imageUrl")),
            price=_optional_float(node.get("price")) or 0,
            old_price=None,
            commission_rate=_optional_float(node.get("commissionRate")) or 0,
            sales_count=_optional_int(node.get("sales")) or 0,
            rating=_optional_float(node.get("ratingStar")),
            niche=niche,
            is_prime_or_free_shipping=False,
            allow_unknown_price=True,
        )
        return self._mapper.map_external_offer(payload)


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
    graphql_url: str = SHOPEE_GRAPHQL_URL
    query: str = SHOPEE_OFFER_LIST_QUERY
    operation_name: str = SHOPEE_OFFER_LIST_OPERATION

    def build(
        self,
        *,
        keyword: str,
        sort_type: int,
        page: int,
        limit: int,
        timestamp: int,
    ) -> HttpRequest:
        return _build_graphql_request(
            graphql_url=self.graphql_url,
            signer=self.signer,
            timestamp=timestamp,
            query=self.query,
            operation_name=self.operation_name,
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
    graphql_url: str = SHOPEE_GRAPHQL_URL

    def build(self, *, origin_url: str, sub_ids: list[str], timestamp: int) -> HttpRequest:
        return _build_graphql_request(
            graphql_url=self.graphql_url,
            signer=self.signer,
            timestamp=timestamp,
            query=SHOPEE_GENERATE_SHORT_LINK_MUTATION,
            operation_name=SHOPEE_GENERATE_SHORT_LINK_OPERATION,
            variables={
                "originUrl": origin_url,
                "subIds": sub_ids,
            },
        )


@dataclass(frozen=True)
class ShopeeGraphqlGateway:
    offer_list_builder: ShopeeOfferListGraphqlRequestBuilder
    short_link_builder: ShopeeShortLinkGraphqlRequestBuilder
    mapper: ShopeeGraphqlOfferMapper
    offer_list_root_field: str = "shopeeOfferV2"
    http_client: ProviderHttpClient = field(default_factory=ProviderHttpClient)
    transport: HttpTransport | None = None
    retry_policy: RetryPolicy | None = None
    sleeper: Sleeper | None = None

    def build_offer_list_request(
        self,
        *,
        keyword: str,
        limit: int,
        timestamp: int,
        page: int = 1,
        sort_type: int = SHOPEE_SORT_LATEST_DESC,
    ) -> HttpRequest:
        validate_positive_limit(limit)
        validate_positive_limit(page)
        return self.offer_list_builder.build(
            keyword=keyword,
            sort_type=sort_type,
            page=page,
            limit=limit,
            timestamp=timestamp,
        )

    def execute_raw_offer_list(
        self,
        *,
        keyword: str,
        limit: int,
        timestamp: int,
        page: int = 1,
        sort_type: int = SHOPEE_SORT_LATEST_DESC,
    ) -> dict[str, Any]:
        request = self.build_offer_list_request(
            keyword=keyword,
            limit=limit,
            timestamp=timestamp,
            page=page,
            sort_type=sort_type,
        )
        return execute_provider_request(
            request=request,
            transport=self.transport,
            http_client=self.http_client,
            provider_name="Shopee",
            retry_policy=self.retry_policy,
            sleeper=self.sleeper,
        )

    def execute_offer_list(
        self,
        *,
        keyword: str,
        niche: str,
        limit: int,
        timestamp: int,
        page: int = 1,
        sort_type: int = SHOPEE_SORT_LATEST_DESC,
    ) -> list[Offer]:
        response_data = self.execute_raw_offer_list(
            keyword=keyword,
            limit=limit,
            timestamp=timestamp,
            page=page,
            sort_type=sort_type,
        )
        return self.normalize_offer_list_response(
            response_data=response_data,
            niche=niche,
            limit=limit,
        )

    def execute_paginated_offer_list(
        self,
        *,
        keyword: str,
        niche: str,
        limit: int,
        page_size: int,
        timestamp: int,
        max_pages: int = 3,
        sort_type: int = SHOPEE_SORT_LATEST_DESC,
    ) -> list[Offer]:
        validate_positive_limit(limit)
        validate_positive_limit(page_size)
        validate_positive_limit(max_pages)

        offers: list[Offer] = []
        page = 1
        while len(offers) < limit and page <= max_pages:
            request_limit = min(page_size, limit - len(offers))
            response_data = self.execute_raw_offer_list(
                keyword=keyword,
                limit=request_limit,
                timestamp=timestamp,
                page=page,
                sort_type=sort_type,
            )
            page_offers = self.normalize_offer_list_response(
            response_data=response_data,
            niche=niche,
            limit=request_limit,
        )
            offers.extend(page_offers)
            if not page_offers or not _has_next_page(
                response_data,
                root_field=self.offer_list_root_field,
            ):
                break
            page += 1

        return offers[:limit]

    def build_short_link_request(
        self,
        *,
        origin_url: str,
        sub_ids: list[str],
        timestamp: int,
    ) -> HttpRequest:
        return self.short_link_builder.build(
            origin_url=origin_url,
            sub_ids=sub_ids,
            timestamp=timestamp,
        )

    def execute_short_link(
        self,
        *,
        origin_url: str,
        sub_ids: list[str],
        timestamp: int,
    ) -> str:
        request = self.build_short_link_request(
            origin_url=origin_url,
            sub_ids=sub_ids,
            timestamp=timestamp,
        )
        response_data = execute_provider_request(
            request=request,
            transport=self.transport,
            http_client=self.http_client,
            provider_name="Shopee",
            retry_policy=self.retry_policy,
            sleeper=self.sleeper,
        )
        return extract_shopee_short_link(response_data)

    def normalize_offer_list_response(
        self,
        *,
        response_data: dict[str, Any],
        niche: str,
        limit: int,
    ) -> list[Offer]:
        validate_positive_limit(limit)
        connection = extract_shopee_offer_connection(
            response_data,
            root_field=self.offer_list_root_field,
        )
        nodes = connection["nodes"]
        return [self.mapper.map_node(node=node, niche=niche) for node in nodes[:limit]]


def extract_shopee_offer_connection(
    response_data: dict[str, Any],
    *,
    root_field: str = "shopeeOfferV2",
) -> dict[str, Any]:
    raise_if_graphql_errors(response_data)

    data = response_data.get("data")
    if not isinstance(data, dict):
        msg = "Shopee GraphQL response field 'data' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    connection = data.get(root_field)
    if not isinstance(connection, dict):
        msg = f"Shopee GraphQL response field 'data.{root_field}' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    nodes = connection.get("nodes")
    if not isinstance(nodes, list):
        msg = f"Shopee GraphQL response field 'data.{root_field}.nodes' must be a list"
        raise ShopeeGraphqlPayloadError(msg)

    page_info = connection.get("pageInfo")
    if not isinstance(page_info, dict):
        msg = f"Shopee GraphQL response field 'data.{root_field}.pageInfo' must be an object"
        raise ShopeeGraphqlPayloadError(msg)

    return connection

def load_shopee_offer_list_query(query_file: str | None) -> str:
    if not query_file:
        return SHOPEE_OFFER_LIST_QUERY

    query = Path(query_file).read_text(encoding="utf-8").strip()
    if not query:
        return SHOPEE_OFFER_LIST_QUERY
    return query


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
    filtered_variables = _filter_declared_graphql_variables(query=query, variables=variables)
    body = {
        "query": query,
        "operationName": operation_name,
        "variables": filtered_variables,
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
    return encode_json_body(body).decode("utf-8")


def build_graphql_request(
    *,
    graphql_url: str,
    signer: ShopeeGraphqlSigner,
    timestamp: int,
    query: str,
    operation_name: str,
    variables: dict[str, Any],
) -> HttpRequest:
    return _build_graphql_request(
        graphql_url=graphql_url,
        signer=signer,
        timestamp=timestamp,
        query=query,
        operation_name=operation_name,
        variables=variables,
    )


def _filter_declared_graphql_variables(*, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    declared_names = set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)\s*:", query))
    if not declared_names:
        return {}
    return {key: value for key, value in variables.items() if key in declared_names}


def _has_next_page(response_data: dict[str, Any], *, root_field: str) -> bool:
    connection = extract_shopee_offer_connection(response_data, root_field=root_field)
    return connection["pageInfo"].get("hasNextPage") is True


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


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _escape_graphql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')

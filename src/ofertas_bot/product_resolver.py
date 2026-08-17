from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from time import time
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.settings import Settings

_SHOPEE_HOSTS = {"shopee.com.br", "www.shopee.com.br", "s.shopee.com.br"}
_ITEM_PATH_PATTERNS = (
    re.compile(r"-i\.(?P<shop_id>\d+)\.(?P<item_id>\d+)(?:[/?#]|$)"),
    re.compile(r"/product/(?P<shop_id>\d+)/(?P<item_id>\d+)(?:[/?#]|$)"),
)


class ShopeeUrlError(ValueError):
    """Raised when a URL cannot be resolved to a Shopee product."""


class ShopeeProductNotFound(LookupError):
    """Raised when Shopee does not return the requested product."""


@dataclass(frozen=True)
class ProductData:
    marketplace: Marketplace
    shop_id: int
    item_id: int
    title: str
    price: float
    old_price: float | None
    discount_pct: float
    images: tuple[str, ...]
    video: str | None
    product_url: str
    affiliate_url: str
    sales: int
    rating: float | None
    commission_rate: float = 0.0
    shop_type_code: int | None = None

    def to_offer(self) -> Offer:
        return Offer(
            marketplace=self.marketplace,
            title=self.title,
            url=self.affiliate_url,
            image_url=self.images[0] if self.images else None,
            price=self.price,
            old_price=self.old_price,
            commission_rate=self.commission_rate,
            sales_count=self.sales,
            rating=self.rating,
            niche="post-offline",
            item_id=self.item_id,
            shop_type_code=self.shop_type_code,
        )


@dataclass
class ShopeeProductResolver:
    settings: Settings
    provider: ShopeeProvider | None = None
    redirect_resolver: Callable[[str], str] | None = None

    def resolve(self, url: str) -> ProductData:
        original_url = _validate_shopee_url(url)
        resolved_url = self._resolve_short_url(original_url)
        shop_id, item_id = extract_shopee_product_ids(resolved_url)
        provider = self.provider or ShopeeProvider(settings=self.settings)
        response = provider.fetch_product_offer_raw_response(
            limit=1,
            item_id=item_id,
            shop_id=shop_id,
        )
        node = _extract_product_node(response)

        returned_item_id = _int_value(node.get("itemId")) or item_id
        returned_shop_id = _int_value(node.get("shopId")) or shop_id
        price = _float_value(node.get("price")) or 0.0
        discount_pct = _normalize_discount(node.get("priceDiscountRate"))
        old_price = _extract_old_price(node, price=price, discount_pct=discount_pct)
        product_url = _text(node.get("productLink")) or resolved_url
        affiliate_url = self._affiliate_url(provider, product_url)
        image = _text(node.get("imageUrl"))

        return ProductData(
            marketplace=Marketplace.SHOPEE,
            shop_id=returned_shop_id,
            item_id=returned_item_id,
            title=_text(node.get("productName")) or _text(node.get("shopName")) or "Produto Shopee",
            price=price,
            old_price=old_price,
            discount_pct=discount_pct,
            images=(image,) if image else (),
            video=_text(node.get("videoUrl")),
            product_url=product_url,
            affiliate_url=affiliate_url,
            sales=_int_value(node.get("sales")) or 0,
            rating=_float_value(node.get("ratingStar")),
            commission_rate=_float_value(node.get("commissionRate")) or 0.0,
            shop_type_code=_int_value(node.get("shopType")),
        )

    def _resolve_short_url(self, url: str) -> str:
        if urlparse(url).netloc.lower() != "s.shopee.com.br":
            return url
        if self.redirect_resolver is not None:
            return self.redirect_resolver(url)
        if not self.settings.enable_real_http:
            raise ShopeeUrlError(
                "Link curto Shopee exige resolucao HTTP. Use a URL completa ou habilite ENABLE_REAL_HTTP."
            )
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=15) as response:  # noqa: S310
            return response.geturl()

    def _affiliate_url(self, provider: ShopeeProvider, product_url: str) -> str:
        sub_ids = [self.settings.shopee_tracking_id] if self.settings.shopee_tracking_id else []
        public_generator = getattr(provider, "generate_short_link", None)
        if callable(public_generator):
            return str(public_generator(origin_url=product_url, sub_ids=sub_ids))
        gateway = provider._get_graphql_gateway()
        if gateway.transport is None:
            raise NotImplementedError(
                "Shopee GraphQL transport is not configured. Enable real HTTP to generate affiliate links."
            )
        return gateway.execute_short_link(
            origin_url=product_url,
            sub_ids=sub_ids,
            timestamp=int(time()),
        )


def extract_shopee_product_ids(url: str) -> tuple[int, int]:
    parsed = urlparse(_validate_shopee_url(url))
    for pattern in _ITEM_PATH_PATTERNS:
        match = pattern.search(parsed.path)
        if match:
            return int(match.group("shop_id")), int(match.group("item_id"))

    query = parse_qs(parsed.query)
    shop_id = _first_int(query, "shopid", "shop_id")
    item_id = _first_int(query, "itemid", "item_id")
    if shop_id is not None and item_id is not None:
        return shop_id, item_id
    raise ShopeeUrlError(
        "Nao foi possivel identificar shop_id e item_id na URL Shopee. Use uma URL completa do produto."
    )


def _validate_shopee_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in _SHOPEE_HOSTS:
        raise ShopeeUrlError("A entrada deve ser uma URL valida de shopee.com.br ou s.shopee.com.br.")
    return url


def _extract_product_node(response: dict[str, object]) -> dict[str, object]:
    data = response.get("data")
    connection = data.get("productOfferV2") if isinstance(data, dict) else None
    nodes = connection.get("nodes") if isinstance(connection, dict) else None
    if not isinstance(nodes, list) or not nodes or not isinstance(nodes[0], dict):
        raise ShopeeProductNotFound("Shopee nao retornou o produto solicitado em productOfferV2.")
    return nodes[0]


def _extract_old_price(node: dict[str, object], *, price: float, discount_pct: float) -> float | None:
    for key in ("priceBeforeDiscount", "originalPrice", "priceOriginal"):
        value = _float_value(node.get(key))
        if value is not None and value > price:
            return value
    if price > 0 and 0 < discount_pct < 100:
        return round(price / (1 - discount_pct / 100), 2)
    return None


def _normalize_discount(value: object) -> float:
    discount = _float_value(value) or 0.0
    if 0 < discount <= 1:
        discount *= 100
    return max(0.0, min(discount, 100.0))


def _first_int(query: dict[str, list[str]], *keys: str) -> int | None:
    for key in keys:
        values = query.get(key)
        if values:
            try:
                return int(values[0])
            except (TypeError, ValueError):
                pass
    return None


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _float_value(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_value(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

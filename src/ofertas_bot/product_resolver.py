from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ofertas_bot.models import Marketplace, Offer

_SHOPEE_HOSTS = {"shopee.com.br", "www.shopee.com.br", "s.shopee.com.br"}
_ITEM_PATH_PATTERNS = (
    re.compile(r"-i\.(?P<shop_id>\d+)\.(?P<item_id>\d+)(?:[/?#]|$)"),
    re.compile(r"/product/(?P<shop_id>\d+)/(?P<item_id>\d+)(?:[/?#]|$)"),
)
_META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE | re.DOTALL)
_ATTR_RE = re.compile(
    r"(?P<key>[\w:-]+)\s*=\s*([\"'])(?P<value>.*?)\2",
    re.IGNORECASE | re.DOTALL,
)
_TITLE_RE = re.compile(r"<title\b[^>]*>(?P<value>.*?)</title>", re.IGNORECASE | re.DOTALL)
_JSON_LD_RE = re.compile(
    r'<script\s+[^>]*type=["\']application/ld\+json["\'][^>]*>(?P<body>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


class ShopeeUrlError(ValueError):
    """Raised when the supplied URL is not a public Shopee URL."""


class ShopeePublicPageError(RuntimeError):
    """Raised when required product facts cannot be extracted from the public page."""


@dataclass(frozen=True)
class ProductData:
    marketplace: Marketplace
    affiliate_url: str
    resolved_url: str
    title: str
    description: str | None
    price: float
    old_price: float | None
    discount_pct: float
    images: tuple[str, ...]
    videos: tuple[str, ...]
    rating: float | None
    rating_count: int | None
    sales: int | None
    shop_name: str | None
    shop_id: int | None = None
    item_id: int | None = None

    def to_offer(self) -> Offer:
        return Offer(
            marketplace=self.marketplace,
            title=self.title,
            url=self.affiliate_url,
            image_url=self.images[0] if self.images else None,
            price=self.price,
            old_price=self.old_price,
            commission_rate=0.0,
            sales_count=self.sales or 0,
            rating=self.rating,
            niche="post-offline",
            item_id=self.item_id,
        )

    @property
    def package_key(self) -> str:
        if self.item_id is not None:
            return str(self.item_id)
        return hashlib.sha256(self.affiliate_url.encode("utf-8")).hexdigest()[:16]


@dataclass
class ShopeePublicPageResolver:
    page_fetcher: Callable[[str], tuple[str, str]] | None = None

    def resolve(self, affiliate_url: str) -> ProductData:
        supplied_url = _validate_shopee_url(affiliate_url)
        resolved_url, html = (self.page_fetcher or fetch_public_page)(supplied_url)
        _validate_shopee_url(resolved_url)
        structured = _extract_structured_product(html)
        meta = _extract_meta(html)
        shop_id, item_id = extract_shopee_product_ids(resolved_url)

        title = _first_text(
            structured.get("name"),
            meta.get("og:title"),
            meta.get("twitter:title"),
            _extract_title(html),
            _search_string(html, ("productName", "product_name")),
        )
        price = _first_float(
            _nested(structured, "offers", "price"),
            _nested(structured, "offers", "lowPrice"),
            meta.get("product:price:amount"),
            _search_number(html, ("price", "priceMin")),
        )
        if not title:
            raise ShopeePublicPageError(
                "Nao foi possivel extrair o titulo da resposta publica da Shopee. "
                f"URL final: {resolved_url}. HTML recebido: {len(html)} bytes. "
                "A pagina pode ter sido entregue como shell JavaScript ou challenge anti-bot."
            )
        if price is None:
            raise ShopeePublicPageError(
                "Nao foi possivel extrair o preco da resposta publica da Shopee. "
                f"URL final: {resolved_url}. HTML recebido: {len(html)} bytes."
            )

        old_price = _first_float(
            meta.get("product:original_price:amount"),
            _search_number(html, ("priceBeforeDiscount", "originalPrice", "priceOriginal")),
        )
        if old_price is not None and old_price <= price:
            old_price = None

        images = _collect_urls(
            structured.get("image"),
            meta.get("og:image"),
            meta.get("twitter:image"),
            _search_urls(html, ("imageUrl",), media="image"),
        )
        videos = _collect_urls(
            structured.get("video"),
            meta.get("og:video"),
            meta.get("og:video:url"),
            _search_urls(html, ("videoUrl", "video_url"), media="video"),
        )

        return ProductData(
            marketplace=Marketplace.SHOPEE,
            affiliate_url=supplied_url,
            resolved_url=resolved_url,
            title=title,
            description=_first_text(
                structured.get("description"),
                meta.get("og:description"),
                meta.get("description"),
            ),
            price=price,
            old_price=old_price,
            discount_pct=_discount_percent(price, old_price),
            images=images,
            videos=videos,
            rating=_first_float(
                _nested(structured, "aggregateRating", "ratingValue"),
                _search_number(html, ("ratingStar", "ratingValue")),
            ),
            rating_count=_first_int(
                _nested(structured, "aggregateRating", "ratingCount"),
                _nested(structured, "aggregateRating", "reviewCount"),
            ),
            sales=_first_int(_search_number(html, ("historicalSold", "sold", "sales"))),
            shop_name=_first_text(
                _nested(structured, "seller", "name"),
                _nested(structured, "brand", "name"),
                _search_string(html, ("shopName", "sellerName")),
            ),
            shop_id=shop_id,
            item_id=item_id,
        )


def fetch_public_page(url: str) -> tuple[str, str]:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(request, timeout=20) as response:  # noqa: S310
        charset = response.headers.get_content_charset() or "utf-8"
        return response.geturl(), response.read().decode(charset, errors="replace")


def extract_shopee_product_ids(url: str) -> tuple[int | None, int | None]:
    parsed = urlparse(_validate_shopee_url(url))
    for pattern in _ITEM_PATH_PATTERNS:
        match = pattern.search(parsed.path)
        if match:
            return int(match.group("shop_id")), int(match.group("item_id"))
    return None, None


def _validate_shopee_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in _SHOPEE_HOSTS:
        raise ShopeeUrlError(
            "A entrada deve ser uma URL afiliada/publica de shopee.com.br ou s.shopee.com.br."
        )
    return url


def _extract_meta(html: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for tag in _META_TAG_RE.findall(html):
        attrs = {
            match.group("key").lower(): unescape(match.group("value")).strip()
            for match in _ATTR_RE.finditer(tag)
        }
        key = attrs.get("property") or attrs.get("name")
        content = attrs.get("content")
        if key and content:
            result[key.lower()] = content
    return result


def _extract_title(html: str) -> str | None:
    match = _TITLE_RE.search(html)
    if not match:
        return None
    value = re.sub(r"\s+", " ", unescape(match.group("value"))).strip()
    return value or None


def _extract_structured_product(html: str) -> dict[str, object]:
    for match in _JSON_LD_RE.finditer(html):
        try:
            payload = json.loads(unescape(match.group("body")).strip())
        except (json.JSONDecodeError, TypeError):
            continue
        for candidate in _walk_json_ld(payload):
            kind = candidate.get("@type")
            kinds = kind if isinstance(kind, list) else [kind]
            if "Product" in kinds:
                return candidate
    return {}


def _walk_json_ld(value: object) -> Iterator[dict[str, object]]:
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _walk_json_ld(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json_ld(item)


def _nested(value: object, *keys: str) -> object | None:
    current = value
    for key in keys:
        if isinstance(current, list):
            current = current[0] if current else None
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _search_number(html: str, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        pattern = re.compile(
            rf'["\']{re.escape(key)}["\']\s*:\s*["\']?(?P<value>\d+(?:\.\d+)?)',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if match:
            return float(match.group("value"))
    return None


def _search_string(html: str, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        pattern = re.compile(
            rf'["\']{re.escape(key)}["\']\s*:\s*["\'](?P<value>.*?)["\']',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if match:
            return unescape(match.group("value")).strip()
    return None


def _search_urls(html: str, keys: tuple[str, ...], *, media: str) -> tuple[str, ...]:
    image_extensions = (".jpg", ".jpeg", ".png", ".webp")
    video_extensions = (".mp4", ".m3u8", ".webm")
    extensions = image_extensions if media == "image" else video_extensions
    found: list[str] = []
    for key in keys:
        pattern = re.compile(
            rf'["\']{re.escape(key)}["\']\s*:\s*["\'](?P<value>https?:\\?/\\?/.*?)["\']',
            re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            url = match.group("value").replace("\\/", "/")
            if any(ext in url.lower() for ext in extensions):
                found.append(url)
    return tuple(found)


def _collect_urls(*values: object) -> tuple[str, ...]:
    result: list[str] = []

    def add(value: object) -> None:
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            if value not in result:
                result.append(value)
        elif isinstance(value, dict):
            add(value.get("contentUrl"))
            add(value.get("url"))
        elif isinstance(value, (list, tuple)):
            for item in value:
                add(item)

    for value in values:
        add(value)
    return tuple(result)


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return unescape(value).strip()
    return None


def _first_float(*values: object) -> float | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_int(*values: object) -> int | None:
    value = _first_float(*values)
    return int(value) if value is not None else None


def _discount_percent(price: float, old_price: float | None) -> float:
    if old_price is None or old_price <= price:
        return 0.0
    return round(((old_price - price) / old_price) * 100, 2)

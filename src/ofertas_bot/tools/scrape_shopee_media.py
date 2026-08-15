from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_OUTPUT_PATH = Path("tmp/shopee_media.csv")
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_IMAGE_HOST = "https://cf.shopee.com.br/file/"
ALLOWED_MEDIA_HOST_SUFFIXES = (
    ".susercontent.com",
    ".susercontent.com.br",
    ".shopee.com.br",
)
CSV_FIELDNAMES = [
    "scraped_at",
    "source_url",
    "item_id",
    "shop_id",
    "media_type",
    "position",
    "media_url",
    "status",
    "http_status",
    "content_type",
    "content_length",
    "error_detail",
]

_FULL_VIDEO_URL_RE = re.compile(r"https?://[^\s\"'<>]+?\.mp4(?:\?[^\s\"'<>]*)?", re.I)
_FULL_IMAGE_URL_RE = re.compile(
    r"https?://[^\s\"'<>]+?susercontent(?:\.com|\.com\.br)/file/[A-Za-z0-9_.-]+",
    re.I,
)
_IMAGES_ARRAY_RE = re.compile(r'"images"\s*:\s*\[(.*?)\]', re.I | re.S)
_PRODUCT_IMAGE_ARRAY_RE = re.compile(
    r'"(?P<name>images|long_images)"\s*:\s*\[(?P<body>.*?)\]',
    re.I | re.S,
)
_IMAGE_FIELD_RE = re.compile(r'"(?:image|image_hash|imageHash)"\s*:\s*"([^"]+)"', re.I)
_QUOTED_VALUE_RE = re.compile(r'"([^"]+)"')
_UNICODE_ESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
_SHOPEE_PRODUCT_RE = re.compile(r"/product/(\d+)/(\d+)")
_SHOPEE_ITEM_RE = re.compile(r"(?:^|/)i\.(\d+)\.(\d+)(?:$|[/?])")
_HTML_TAG_RE = re.compile(r"<(?P<closing>/)?(?P<tag>[a-zA-Z][a-zA-Z0-9-]*)(?P<attrs>[^>]*)>")
_ATTR_RE = re.compile(
    r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s"\'=<>`]+))'
)


class ShopeeMediaScrapeError(RuntimeError):
    """Raised when Shopee media scraping cannot continue."""


@dataclass(frozen=True)
class MediaAsset:
    media_type: str
    position: int
    media_url: str
    status: str = "not_validated"
    http_status: int | None = None
    content_type: str | None = None
    content_length: str | None = None
    error_detail: str | None = None


@dataclass(frozen=True)
class ScrapeResult:
    source_url: str
    item_id: str | None
    shop_id: str | None
    scraped_at: datetime
    assets: list[MediaAsset]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrai URLs publicas de imagens e videos de uma pagina de produto Shopee."
    )
    parser.add_argument("--url", required=True, help="URL publica do produto Shopee")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--item-id", default=None)
    parser.add_argument("--shop-id", default=None)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Nao valida URLs de midia com requisicao HTTP leve.",
    )
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    opener: Callable[..., Any] = urlopen,
) -> int:
    args = build_parser().parse_args(argv)

    try:
        result = scrape_shopee_media(
            source_url=args.url,
            output_path=args.output,
            item_id=args.item_id,
            shop_id=args.shop_id,
            timeout_seconds=args.timeout,
            validate=not args.no_validate,
            opener=opener,
        )
    except ShopeeMediaScrapeError as error:
        print(f"ERRO | {error}", file=sys.stderr)
        return 2

    print("INFO | Midias Shopee salvas")
    print(f"INFO | output={args.output.as_posix()}")
    print(f"INFO | total_assets={len(result.assets)}")
    print(f"INFO | videos={sum(asset.media_type == 'video' for asset in result.assets)}")
    print(f"INFO | images={sum(asset.media_type == 'image' for asset in result.assets)}")
    print("INFO | Nenhum arquivo de midia foi baixado.")
    return 0


def scrape_shopee_media(
    *,
    source_url: str,
    output_path: Path,
    item_id: str | None = None,
    shop_id: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    validate: bool = True,
    opener: Callable[..., Any] = urlopen,
) -> ScrapeResult:
    resolved_shop_id, resolved_item_id = resolve_product_ids(
        source_url=source_url,
        explicit_shop_id=shop_id,
        explicit_item_id=item_id,
    )
    html_text = fetch_text(
        source_url,
        timeout_seconds=timeout_seconds,
        opener=opener,
    )
    assets = extract_media_assets(
        html_text,
        item_id=resolved_item_id,
        shop_id=resolved_shop_id,
    )
    if validate:
        assets = [
            validate_media_asset(
                asset,
                timeout_seconds=timeout_seconds,
                opener=opener,
            )
            for asset in assets
        ]

    result = ScrapeResult(
        source_url=source_url,
        item_id=resolved_item_id,
        shop_id=resolved_shop_id,
        scraped_at=datetime.now(UTC),
        assets=assets,
    )
    write_media_csv(output_path=output_path, result=result)
    return result


def fetch_text(
    url: str,
    *,
    timeout_seconds: float,
    opener: Callable[..., Any],
) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
        method="GET",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            raw_body = response.read()
    except HTTPError as error:
        raise ShopeeMediaScrapeError(f"pagina Shopee retornou HTTP {error.code}") from error
    except URLError as error:
        raise ShopeeMediaScrapeError(f"falha ao acessar pagina Shopee: {error}") from error
    return raw_body.decode("utf-8", errors="replace")


def extract_media_assets(
    raw_html: str,
    *,
    item_id: str | None = None,
    shop_id: str | None = None,
) -> list[MediaAsset]:
    text = scope_product_html(normalize_html(raw_html), item_id=item_id, shop_id=shop_id)
    candidates: list[tuple[int, str, str]] = []

    for match in _FULL_VIDEO_URL_RE.finditer(text):
        candidates.append((match.start(), "video", clean_media_url(match.group(0))))

    for match in _FULL_IMAGE_URL_RE.finditer(text):
        candidates.append((match.start(), "image", clean_media_url(match.group(0))))

    for position, image_id in extract_image_ids(text):
        candidates.append((position, "image", f"{DEFAULT_IMAGE_HOST}{image_id}"))

    seen: set[tuple[str, str]] = set()
    assets: list[MediaAsset] = []
    for _, media_type, media_url in sorted(
        candidates,
        key=lambda item: (item[1] == "video", item[0]),
    ):
        if not is_allowed_media_url(media_url):
            continue
        key = (
            media_type,
            canonical_video_key(media_url) if media_type == "video" else media_url,
        )
        if key in seen:
            continue
        seen.add(key)
        assets.append(
            MediaAsset(
                media_type=media_type,
                position=len(assets) + 1,
                media_url=media_url,
            )
        )
    return assets


def scope_product_html(
    text: str,
    *,
    item_id: str | None = None,
    shop_id: str | None = None,
) -> str:
    video_parts = extract_product_video_fragments(text, item_id=item_id, shop_id=shop_id)
    product_parts: list[str] = []
    main_html = extract_first_element(
        text,
        tag_name="div",
        predicate=lambda attrs: attrs.get("role") == "main"
        and class_contains(attrs.get("class"), {"container"}),
    )
    if main_html is None:
        image_parts = extract_product_image_fragments(text, item_id=item_id, shop_id=shop_id)
        product_parts.extend(image_parts)
        product_parts.extend(video_parts)
        return "\n".join(product_parts) if product_parts else text

    card_parts = extract_all_elements(
        main_html,
        tag_name="div",
        predicate=lambda attrs: class_contains(attrs.get("class"), {"flex", "card", "vr0998"}),
    )
    product_parts.extend(card_parts)
    if not card_parts:
        product_parts.extend(
            extract_product_image_fragments(text, item_id=item_id, shop_id=shop_id)
        )
    product_parts.extend(video_parts)
    product_parts.extend(
        extract_all_elements(
            main_html,
            tag_name="video",
            predicate=lambda attrs: class_contains(attrs.get("class"), {"QODm2C", "exqDJH"}),
        )
    )
    return "\n".join(product_parts) if product_parts else main_html


def extract_product_image_fragments(
    text: str,
    *,
    item_id: str | None,
    shop_id: str | None,
    radius: int = 3_000,
) -> list[str]:
    if not item_id:
        return []

    best_images: tuple[int, int, list[str]] | None = None
    best_long_images: tuple[int, int, list[str]] | None = None
    for match in _PRODUCT_IMAGE_ARRAY_RE.finditer(text):
        image_ids = [
            value_match.group(1)
            for value_match in _QUOTED_VALUE_RE.finditer(match.group("body"))
            if looks_like_shopee_image_id(value_match.group(1))
        ]
        if not image_ids:
            continue

        start = max(0, match.start() - radius)
        end = min(len(text), match.end() + radius)
        window = text[start:end]
        if str(item_id) not in window:
            continue
        if shop_id and str(shop_id) not in window:
            continue
        previous_context = text[max(0, match.start() - 600) : match.start()]
        if (
            match.group("name").lower() == "images"
            and '"tier_variations"' in previous_context
            and '"liked_count"' not in previous_context
            and '"product_images"' not in previous_context
        ):
            continue

        candidate = (len(image_ids), match.start(), image_ids)
        name = match.group("name").lower()
        if name == "images" and (best_images is None or candidate[:2] > best_images[:2]):
            best_images = candidate
        if name == "long_images" and (
            best_long_images is None or candidate[:2] > best_long_images[:2]
        ):
            best_long_images = candidate

    image_ids = select_product_image_ids(best_images, best_long_images)
    if not image_ids:
        return []
    quoted_ids = ",".join(f'"{image_id}"' for image_id in image_ids)
    return [f'"images":[{quoted_ids}]']


def select_product_image_ids(
    images: tuple[int, int, list[str]] | None,
    long_images: tuple[int, int, list[str]] | None,
) -> list[str]:
    if images is None:
        return long_images[2] if long_images is not None else []
    if long_images is None:
        return images[2]

    image_ids = images[2]
    long_image_ids = long_images[2]
    if len(image_ids) == 1:
        return long_image_ids
    if len(image_ids) > len(long_image_ids):
        return long_image_ids
    return image_ids


def extract_product_video_fragments(
    text: str,
    *,
    item_id: str | None,
    shop_id: str | None,
    radius: int = 20_000,
) -> list[str]:
    if not item_id:
        return []

    fragments: list[str] = []
    seen_urls: set[str] = set()
    seen_ranges: set[tuple[int, int]] = set()
    for match in re.finditer(re.escape(str(item_id)), text):
        start = max(0, match.start() - radius)
        end = min(len(text), match.end() + radius)
        window = text[start:end]
        if shop_id and str(shop_id) not in window:
            continue
        if "images" not in window and "video_info_list" not in window:
            continue
        key = (start, end)
        if key in seen_ranges:
            continue
        seen_ranges.add(key)
        for video_match in _FULL_VIDEO_URL_RE.finditer(window):
            video_url = clean_media_url(video_match.group(0))
            if video_url in seen_urls:
                continue
            seen_urls.add(video_url)
            fragments.append(video_url)
    return fragments


def extract_all_elements(
    text: str,
    *,
    tag_name: str,
    predicate: Callable[[dict[str, str]], bool],
) -> list[str]:
    normalized_tag = tag_name.lower()
    elements: list[str] = []
    search_start = 0
    while search_start < len(text):
        selected_match: re.Match[str] | None = None
        for match in _HTML_TAG_RE.finditer(text, search_start):
            if match.group("closing"):
                continue
            tag = match.group("tag").lower()
            if tag != normalized_tag:
                continue
            attrs = parse_html_attrs(match.group("attrs"))
            if predicate(attrs):
                selected_match = match
                break

        if selected_match is None:
            break

        end_index = find_matching_end_tag(
            text,
            start_match=selected_match,
            tag_name=normalized_tag,
        )
        if end_index is None:
            elements.append(text[selected_match.start() :])
            break

        elements.append(text[selected_match.start() : end_index])
        search_start = end_index

    return elements


def extract_first_element(
    text: str,
    *,
    tag_name: str,
    predicate: Callable[[dict[str, str]], bool],
) -> str | None:
    normalized_tag = tag_name.lower()
    for match in _HTML_TAG_RE.finditer(text):
        if match.group("closing"):
            continue
        tag = match.group("tag").lower()
        if tag != normalized_tag:
            continue
        attrs = parse_html_attrs(match.group("attrs"))
        if not predicate(attrs):
            continue
        end_index = find_matching_end_tag(text, start_match=match, tag_name=normalized_tag)
        if end_index is None:
            return text[match.start() :]
        return text[match.start() : end_index]
    return None


def find_matching_end_tag(
    text: str,
    *,
    start_match: re.Match[str],
    tag_name: str,
) -> int | None:
    depth = 0
    for match in _HTML_TAG_RE.finditer(text, start_match.start()):
        tag = match.group("tag").lower()
        if tag != tag_name:
            continue
        if match.group("closing"):
            depth -= 1
            if depth == 0:
                return match.end()
        else:
            depth += 1
    return None


def parse_html_attrs(raw_attrs: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in _ATTR_RE.finditer(raw_attrs):
        name = match.group(1).lower()
        value = match.group(3) or match.group(4) or match.group(5) or ""
        attrs[name] = html.unescape(value)
    return attrs


def class_contains(class_value: str | None, expected_classes: set[str]) -> bool:
    actual_classes = set((class_value or "").split())
    return expected_classes <= actual_classes


def normalize_html(raw_html: str) -> str:
    text = raw_html
    for _ in range(3):
        text = html.unescape(text)
        text = text.replace("\\/", "/")
        text = _UNICODE_ESCAPE_RE.sub(lambda match: chr(int(match.group(1), 16)), text)
    return text


def extract_image_ids(text: str) -> list[tuple[int, str]]:
    values: list[tuple[int, str]] = []
    for match in _IMAGES_ARRAY_RE.finditer(text):
        values.extend(
            (match.start(1) + value_match.start(1), value_match.group(1))
            for value_match in _QUOTED_VALUE_RE.finditer(match.group(1))
        )
    values.extend((match.start(1), match.group(1)) for match in _IMAGE_FIELD_RE.finditer(text))
    return [(position, value) for position, value in values if looks_like_shopee_image_id(value)]


def looks_like_shopee_image_id(value: str) -> bool:
    if value.startswith("http://") or value.startswith("https://"):
        return False
    if "/" in value or "\\" in value:
        return False
    if re.fullmatch(r"[a-f0-9]{32}", value, re.I):
        return True
    return bool(re.fullmatch(r"(?:br|sg|cn)-[A-Za-z0-9_.-]{12,}", value))


def validate_media_asset(
    asset: MediaAsset,
    *,
    timeout_seconds: float,
    opener: Callable[..., Any],
) -> MediaAsset:
    request = Request(
        asset.media_url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Range": "bytes=0-0",
        },
        method="GET",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            response.read(1)
            http_status = status_code(response)
            content_type = header_value(response, "Content-Type")
            content_length = header_value(response, "Content-Length")
    except HTTPError as error:
        return MediaAsset(
            media_type=asset.media_type,
            position=asset.position,
            media_url=asset.media_url,
            status="failed",
            http_status=error.code,
            error_detail=f"HTTP {error.code}",
        )
    except URLError as error:
        return MediaAsset(
            media_type=asset.media_type,
            position=asset.position,
            media_url=asset.media_url,
            status="failed",
            error_detail=str(error),
        )

    expected_prefix = "video/" if asset.media_type == "video" else "image/"
    validation_status = (
        "valid"
        if 200 <= http_status < 400 and (content_type or "").lower().startswith(expected_prefix)
        else "unexpected_content_type"
    )
    return MediaAsset(
        media_type=asset.media_type,
        position=asset.position,
        media_url=asset.media_url,
        status=validation_status,
        http_status=http_status,
        content_type=content_type,
        content_length=content_length,
    )


def write_media_csv(*, output_path: Path, result: ScrapeResult) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for asset in result.assets:
            writer.writerow(
                {
                    "scraped_at": result.scraped_at.isoformat(),
                    "source_url": result.source_url,
                    "item_id": result.item_id or "",
                    "shop_id": result.shop_id or "",
                    "media_type": asset.media_type,
                    "position": asset.position,
                    "media_url": asset.media_url,
                    "status": asset.status,
                    "http_status": asset.http_status or "",
                    "content_type": asset.content_type or "",
                    "content_length": asset.content_length or "",
                    "error_detail": asset.error_detail or "",
                }
            )


def resolve_product_ids(
    *,
    source_url: str,
    explicit_shop_id: str | None,
    explicit_item_id: str | None,
) -> tuple[str | None, str | None]:
    shop_id = explicit_shop_id
    item_id = explicit_item_id
    for pattern in (_SHOPEE_PRODUCT_RE, _SHOPEE_ITEM_RE):
        match = pattern.search(source_url)
        if match:
            shop_id = shop_id or match.group(1)
            item_id = item_id or match.group(2)
            break
    return shop_id, item_id


def clean_media_url(value: str) -> str:
    return value.rstrip("\\\",;)")


def canonical_video_key(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path
    path = re.sub(r"\.default\.mp4$", ".mp4", path)
    path = re.sub(r"\.\d+\.mp4$", ".mp4", path)
    return path


def is_allowed_media_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    return any(host.endswith(suffix) for suffix in ALLOWED_MEDIA_HOST_SUFFIXES)


def status_code(response: Any) -> int:
    status = getattr(response, "status", None)
    if isinstance(status, int):
        return status
    return int(response.getcode())


def header_value(response: Any, name: str) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is not None:
        value = headers.get(name)
        if value is not None:
            return str(value)
    getheader = getattr(response, "getheader", None)
    if getheader is not None:
        value = getheader(name)
        if value is not None:
            return str(value)
    return None


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

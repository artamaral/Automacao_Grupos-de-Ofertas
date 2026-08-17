from __future__ import annotations

import io
import textwrap
from collections.abc import Callable
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps

from ofertas_bot.product_resolver import ProductData


class OfflineMediaError(RuntimeError):
    """Raised when an offline media artifact cannot be generated."""


def load_product_image(
    product: ProductData,
    *,
    image_fetcher: Callable[[str], bytes] | None = None,
) -> Image.Image:
    if not product.images:
        return placeholder_image((1080, 1080), "Imagem nao disponivel")
    fetcher = image_fetcher or download_bytes
    try:
        image = Image.open(io.BytesIO(fetcher(product.images[0])))
        image.load()
        return image.convert("RGB")
    except Exception as exc:
        raise OfflineMediaError(f"Falha ao baixar/abrir imagem do produto: {exc}") from exc


def download_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:  # noqa: S310
        return response.read()


def base_canvas(size: tuple[int, int]) -> Image.Image:
    return Image.new("RGB", size, "white")


def placeholder_image(size: tuple[int, int], text: str) -> Image.Image:
    image = base_canvas(size)
    draw_centered(ImageDraw.Draw(image), text, y=size[1] // 2 - 30, size=44, width=size[0] - 120)
    return image


def paste_product_image(
    canvas: Image.Image,
    image: Image.Image,
    *,
    box: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = box
    target = ImageOps.contain(image, (right - left, bottom - top))
    x = left + (right - left - target.width) // 2
    y = top + (bottom - top - target.height) // 2
    canvas.paste(target, (x, y))


def draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    y: int,
    size: int,
    width: int,
) -> None:
    font = ImageFont.load_default(size=size)
    max_chars = max(12, int(width / max(size * 0.56, 1)))
    lines = textwrap.wrap(text, width=max_chars) or [text]
    current_y = y
    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        draw.text(((1080 - line_width) / 2, current_y), line, fill="black", font=font)
        current_y += size + 12


def price_text(product: ProductData) -> str:
    if product.old_price and product.old_price > product.price:
        return f"de R$ {product.old_price:.2f} por R$ {product.price:.2f}"
    return f"R$ {product.price:.2f}"


def short_title(title: str, limit: int = 70) -> str:
    compact = " ".join(title.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from ofertas_bot.generators.common import (
    base_canvas,
    draw_centered,
    paste_product_image,
    price_text,
    short_title,
)
from ofertas_bot.product_resolver import ProductData

STORY_SIZE = (1080, 1920)


def generate_story(directory: Path, product: ProductData, image: Image.Image) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    canvas = base_canvas(STORY_SIZE)
    draw = ImageDraw.Draw(canvas)
    paste_product_image(canvas, image, box=(90, 250, 990, 1120))
    draw_centered(draw, "ACHADINHO SHOPEE", y=90, size=54, width=1000)
    draw_centered(draw, short_title(product.title), y=1160, size=42, width=930)
    draw_centered(draw, price_text(product), y=1370, size=58, width=930)
    if product.discount_pct:
        draw_centered(draw, f"{product.discount_pct:.0f}% OFF", y=1470, size=52, width=930)
    draw_centered(draw, "COMPRE AQUI", y=1580, size=48, width=930)
    draw.rounded_rectangle((250, 1680, 830, 1860), radius=36, outline="black", width=4)
    draw_centered(draw, "AREA PARA LINK STICKER", y=1730, size=34, width=520)
    canvas.save(directory / "story.jpg", quality=94)
    (directory / "link.txt").write_text(product.affiliate_url + "\n", encoding="utf-8")
    (directory / "instructions.txt").write_text(
        "Publique story.jpg manualmente e adicione o Link Sticker do Instagram "
        "na area reservada, usando exatamente a URL de link.txt.\n",
        encoding="utf-8",
    )

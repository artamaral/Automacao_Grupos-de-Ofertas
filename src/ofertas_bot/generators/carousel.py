from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from ofertas_bot.generators.common import base_canvas, draw_centered, paste_product_image, short_title
from ofertas_bot.product_resolver import ProductData

CAROUSEL_SIZE = (1080, 1350)


def generate_carousel(
    directory: Path,
    product: ProductData,
    image: Image.Image,
    *,
    caption: str,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    cards = (
        _product_card(product, image),
        _price_card(product, image),
        _trust_card(product, image),
        _cta_card(product, image),
    )
    for index, card in enumerate(cards, start=1):
        card.save(directory / f"{index:02d}.jpg", quality=94)
    (directory / "caption.txt").write_text(caption + "\n", encoding="utf-8")


def _product_card(product: ProductData, image: Image.Image) -> Image.Image:
    canvas = base_canvas(CAROUSEL_SIZE)
    draw = ImageDraw.Draw(canvas)
    draw_centered(draw, "ACHADINHO SHOPEE", y=60, size=48, width=1000)
    paste_product_image(canvas, image, box=(80, 190, 1000, 940))
    draw_centered(draw, short_title(product.title, 90), y=1000, size=42, width=930)
    return canvas


def _price_card(product: ProductData, image: Image.Image) -> Image.Image:
    canvas = base_canvas(CAROUSEL_SIZE)
    draw = ImageDraw.Draw(canvas)
    paste_product_image(canvas, image, box=(180, 100, 900, 760))
    draw_centered(draw, "OFERTA", y=800, size=48, width=900)
    if product.old_price and product.old_price > product.price:
        draw_centered(draw, f"de R$ {product.old_price:.2f}", y=900, size=42, width=900)
    draw_centered(draw, f"por R$ {product.price:.2f}", y=990, size=68, width=900)
    if product.discount_pct:
        draw_centered(draw, f"{product.discount_pct:.0f}% OFF", y=1100, size=58, width=900)
    return canvas


def _trust_card(product: ProductData, image: Image.Image) -> Image.Image:
    canvas = base_canvas(CAROUSEL_SIZE)
    draw = ImageDraw.Draw(canvas)
    paste_product_image(canvas, image, box=(250, 90, 830, 660))
    draw_centered(draw, "DETALHES DA OFERTA", y=720, size=48, width=950)
    y = 850
    if product.rating is not None:
        draw_centered(draw, f"Avaliacao: {product.rating:.1f}/5", y=y, size=48, width=900)
        y += 100
    if product.sales:
        draw_centered(draw, f"{product.sales} vendas", y=y, size=48, width=900)
        y += 100
    if y == 850:
        draw_centered(draw, "Confira os detalhes no anuncio", y=y, size=42, width=900)
    return canvas


def _cta_card(product: ProductData, image: Image.Image) -> Image.Image:
    canvas = base_canvas(CAROUSEL_SIZE)
    draw = ImageDraw.Draw(canvas)
    paste_product_image(canvas, image, box=(240, 100, 840, 700))
    draw_centered(draw, "GOSTOU?", y=800, size=62, width=900)
    draw_centered(draw, "Confira a oferta pelo link da publicacao", y=930, size=46, width=900)
    draw_centered(draw, "Preco e disponibilidade podem mudar", y=1130, size=34, width=900)
    return canvas

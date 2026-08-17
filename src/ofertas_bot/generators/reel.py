from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw

from ofertas_bot.generators.common import (
    OfflineMediaError,
    base_canvas,
    draw_centered,
    paste_product_image,
    price_text,
    short_title,
)
from ofertas_bot.product_resolver import ProductData

REEL_SIZE = (1080, 1920)


def generate_reel(
    directory: Path,
    product: ProductData,
    image: Image.Image,
    *,
    caption: str,
    renderer: Callable[[Path, Path], None] | None = None,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    cover = base_canvas(REEL_SIZE)
    draw = ImageDraw.Draw(cover)
    paste_product_image(cover, image, box=(70, 250, 1010, 1220))
    draw_centered(draw, "ACHADINHO SHOPEE", y=100, size=54, width=1000)
    draw_centered(draw, short_title(product.title), y=1280, size=42, width=940)
    draw_centered(draw, price_text(product), y=1490, size=60, width=940)
    if product.discount_pct:
        draw_centered(draw, f"{product.discount_pct:.0f}% OFF", y=1600, size=54, width=940)
    draw_centered(draw, "Confira a oferta", y=1740, size=44, width=940)
    cover_path = directory / "cover.jpg"
    cover.save(cover_path, quality=94)
    (directory / "caption.txt").write_text(caption + "\n", encoding="utf-8")
    (renderer or render_reel_with_ffmpeg)(cover_path, directory / "reel.mp4")


def render_reel_with_ffmpeg(cover_path: Path, output_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise OfflineMediaError(
            "FFmpeg nao encontrado. Instale o ffmpeg ou gere apenas --story/--carousel."
        )
    command = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(cover_path),
        "-t",
        "15",
        "-r",
        "30",
        "-vf",
        "scale=1080:1920,format=yuv420p",
        "-an",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise OfflineMediaError(f"FFmpeg falhou ao gerar Reel: {completed.stderr.strip()}")

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from ofertas_bot.agents.copywriter import CopywriterAgent
from ofertas_bot.generators.carousel import generate_carousel
from ofertas_bot.generators.common import load_product_image
from ofertas_bot.generators.preview import generate_preview
from ofertas_bot.generators.reel import generate_reel
from ofertas_bot.generators.story import generate_story
from ofertas_bot.models import ScoredOffer
from ofertas_bot.product_resolver import ProductData

SUPPORTED_FORMATS = frozenset({"reels", "carousel", "story"})


@dataclass(frozen=True)
class GeneratedPostPackage:
    root: Path
    formats: tuple[str, ...]
    caption: str


class OfflinePostGenerator:
    def __init__(
        self,
        *,
        image_fetcher: Callable[[str], bytes] | None = None,
        reel_renderer: Callable[[Path, Path], None] | None = None,
    ) -> None:
        self.image_fetcher = image_fetcher
        self.reel_renderer = reel_renderer

    def generate(
        self,
        product: ProductData,
        *,
        formats: Iterable[str],
        output_dir: Path | str = Path("output"),
        preview: bool = False,
    ) -> GeneratedPostPackage:
        selected = normalize_formats(formats)
        root = Path(output_dir) / str(product.item_id)
        root.mkdir(parents=True, exist_ok=True)

        caption = CopywriterAgent().create_message(
            ScoredOffer(offer=product.to_offer(), score=0.0, reasons=["post offline"])
        ).text
        image = load_product_image(product, image_fetcher=self.image_fetcher)

        if "story" in selected:
            generate_story(root / "story", product, image)
        if "carousel" in selected:
            generate_carousel(root / "carousel", product, image, caption=caption)
        if "reels" in selected:
            generate_reel(
                root / "reels",
                product,
                image,
                caption=caption,
                renderer=self.reel_renderer,
            )

        payload = asdict(product)
        payload["marketplace"] = product.marketplace.value
        payload["formats"] = list(selected)
        (root / "metadata.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if preview:
            generate_preview(root / "preview.html", product, formats=selected, caption=caption)
        return GeneratedPostPackage(root=root, formats=selected, caption=caption)


def normalize_formats(formats: Iterable[str]) -> tuple[str, ...]:
    selected = tuple(dict.fromkeys(value.strip().lower() for value in formats if value.strip()))
    invalid = set(selected) - SUPPORTED_FORMATS
    if invalid:
        raise ValueError(f"Formatos invalidos: {', '.join(sorted(invalid))}")
    if not selected:
        raise ValueError("Selecione ao menos um formato: reels, carousel ou story.")
    return selected

from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image

from ofertas_bot.agents.copywriter import CopywriterAgent
from ofertas_bot.models import Marketplace, ScoredOffer
from ofertas_bot.offline_post_generator import OfflinePostGenerator
from ofertas_bot.product_resolver import ProductData


def _product(*, item_id: int | None = 456) -> ProductData:
    return ProductData(
        marketplace=Marketplace.SHOPEE,
        affiliate_url="https://s.shopee.com.br/affiliate",
        resolved_url="https://shopee.com.br/produto-i.123.456",
        title="Produto teste",
        description="Descricao do produto",
        price=80.0,
        old_price=100.0,
        discount_pct=20.0,
        images=("https://img.test/produto.jpg",),
        videos=("https://video.test/produto.mp4",),
        rating=4.8,
        rating_count=1234,
        sales=321,
        shop_name="Loja teste",
        shop_id=123,
        item_id=item_id,
    )


def _image_bytes(_: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (600, 600), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _fake_reel_renderer(_: Path, output: Path) -> None:
    output.write_bytes(b"fake-mp4")


def test_generate_all_outputs_and_reuses_official_copy(tmp_path: Path) -> None:
    product = _product()
    generator = OfflinePostGenerator(
        image_fetcher=_image_bytes,
        reel_renderer=_fake_reel_renderer,
    )
    package = generator.generate(
        product,
        formats=("reels", "carousel", "story"),
        output_dir=tmp_path,
        preview=True,
    )
    expected_copy = CopywriterAgent().create_message(
        ScoredOffer(offer=product.to_offer(), score=0.0, reasons=["test"])
    ).text
    assert package.caption == expected_copy
    assert (package.root / "reels" / "caption.txt").read_text().strip() == expected_copy
    assert (package.root / "carousel" / "caption.txt").read_text().strip() == expected_copy
    assert (package.root / "story" / "link.txt").read_text().strip() == product.affiliate_url
    assert (package.root / "story" / "story.jpg").exists()
    assert (package.root / "reels" / "reel.mp4").read_bytes() == b"fake-mp4"
    assert (package.root / "preview.html").exists()
    metadata = json.loads((package.root / "metadata.json").read_text())
    assert metadata["affiliate_url"] == product.affiliate_url
    assert metadata["item_id"] == 456


def test_story_is_1080_by_1920(tmp_path: Path) -> None:
    package = OfflinePostGenerator(image_fetcher=_image_bytes).generate(
        _product(), formats=("story",), output_dir=tmp_path
    )
    with Image.open(package.root / "story" / "story.jpg") as image:
        assert image.size == (1080, 1920)


def test_package_does_not_require_item_id(tmp_path: Path) -> None:
    product = _product(item_id=None)
    package = OfflinePostGenerator(image_fetcher=_image_bytes).generate(
        product, formats=("story",), output_dir=tmp_path
    )
    assert package.root.name == product.package_key
    assert package.root.name != "None"

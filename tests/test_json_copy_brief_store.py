import json

from ofertas_bot.copy_brief import build_copy_brief
from ofertas_bot.models import Marketplace, Offer, RefreshChangedItem, ScoredOffer
from ofertas_bot.storage.json_copy_brief_store import JsonCopyBriefStore


def make_scored_offer() -> ScoredOffer:
    offer = Offer(
        marketplace=Marketplace.SHOPEE,
        title="Produto teste",
        url="https://example.com/produto",
        image_url=None,
        price=50,
        old_price=100,
        commission_rate=0.08,
        sales_count=1000,
        rating=4.8,
        niche="mae e bebe",
        shop_type_code=2,
    )
    return ScoredOffer(
        offer=offer,
        score=43,
        reasons=["desconto de 50%", "1000 vendas", "loja star"],
    )


def test_json_copy_brief_store_saves_gpt_ready_contract(tmp_path) -> None:
    path = tmp_path / "copy_briefs.json"
    brief = build_copy_brief(
        make_scored_offer(),
        refresh_iterations=2,
        refresh_stability_reached=True,
        refresh_changed_items=(
            RefreshChangedItem(
                item_id=123,
                title="Produto teste",
                refresh_iteration=1,
                changed_fields=("price", "commission_rate"),
            ),
        ),
    )

    JsonCopyBriefStore(path=path).save((brief,))

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload[0]["content_type"] == "product_offer"
    assert payload[0]["facts"]["title"] == "Produto teste"
    assert payload[0]["facts"]["marketplace"] == "shopee"
    assert payload[0]["facts"]["discount_percent"] == 50
    assert payload[0]["selection"] == {
        "score": 43,
        "reasons": ["desconto de 50%", "1000 vendas", "loja star"],
    }
    assert payload[0]["required_disclosures"]
    assert payload[0]["copy_constraints"]
    assert payload[0]["forbidden_claims"]
    assert payload[0]["refresh"] == {
        "iterations": 2,
        "stability_reached": True,
        "changed_items": [
            {
                "item_id": 123,
                "title": "Produto teste",
                "refresh_iteration": 1,
                "changed_fields": ["price", "commission_rate"],
            }
        ],
    }


def test_json_copy_brief_store_loads_saved_briefs(tmp_path) -> None:
    path = tmp_path / "copy_briefs.json"
    brief = build_copy_brief(
        make_scored_offer(),
        refresh_iterations=2,
        refresh_stability_reached=False,
        refresh_changed_items=(
            RefreshChangedItem(
                item_id=123,
                title="Produto teste",
                refresh_iteration=1,
                changed_fields=("price",),
            ),
        ),
    )
    JsonCopyBriefStore(path=path).save((brief,))

    loaded = JsonCopyBriefStore(path=path).load()

    assert len(loaded) == 1
    assert loaded[0].offer.title == "Produto teste"
    assert loaded[0].score == 43
    assert loaded[0].score_reasons == ("desconto de 50%", "1000 vendas", "loja star")
    assert loaded[0].refresh_iterations == 2
    assert loaded[0].refresh_stability_reached is False
    assert loaded[0].refresh_changed_items[0].item_id == 123
    assert loaded[0].refresh_changed_items[0].changed_fields == ("price",)

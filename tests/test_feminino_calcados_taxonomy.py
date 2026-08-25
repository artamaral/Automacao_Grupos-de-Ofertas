from __future__ import annotations

import json
import re
from pathlib import Path

TAXONOMY_PATH = Path(
    "config/catalog-taxonomies/feminino/shopee_feminino_subniches_taxonomia_base.json"
)
CALCADOS_SUBNICHES = {
    "calcados-sandalia",
    "calcados-sapatilha",
    "calcados-chinelo",
    "calcados-rasteirinha",
    "calcados-mocassim",
}


def test_feminino_taxonomy_accepts_exact_calcados_subniches() -> None:
    taxonomy = _load_taxonomy()

    assert len(taxonomy["allowed_subniches"]) == 37
    assert CALCADOS_SUBNICHES <= set(taxonomy["allowed_subniches"])
    assert "calcados-sandal" not in taxonomy["allowed_subniches"]


def test_feminino_taxonomy_maps_sandal_to_sandalia() -> None:
    taxonomy = _load_taxonomy()

    assert taxonomy["source_keyword_to_subniche"]["sandal"] == "calcados-sandalia"
    assert taxonomy["source_keyword_to_subniche"]["sandalia"] == "calcados-sandalia"
    assert taxonomy["source_keyword_to_subniche"]["sandália"] == "calcados-sandalia"


def test_feminino_taxonomy_classifies_basic_calcados_samples_by_fallback() -> None:
    taxonomy = _load_taxonomy()
    samples = {
        "Sandália Feminina": "calcados-sandalia",
        "Sapatilha Feminina": "calcados-sapatilha",
        "Chinelo Feminino": "calcados-chinelo",
        "Rasteirinha Feminina": "calcados-rasteirinha",
        "Mocassim Feminino": "calcados-mocassim",
    }

    for product_name, expected in samples.items():
        assert _fallback_subniche(taxonomy, product_name) == expected


def test_feminino_taxonomy_preserves_existing_non_calcados_mappings() -> None:
    taxonomy = _load_taxonomy()
    mappings = taxonomy["source_keyword_to_subniche"]

    assert mappings["vestido"] == "moda-vestidos"
    assert mappings["batom"] == "maquiagem-labios"
    assert mappings["bolsa feminina"] == "bolsas-e-carteiras"
    assert mappings["skincare"] == "skincare-facial"


def _load_taxonomy() -> dict:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def _fallback_subniche(taxonomy: dict, product_name: str) -> str | None:
    normalized = product_name.lower()
    for rule in sorted(
        taxonomy["fallback_product_name_rules"],
        key=lambda item: int(item["order"]),
    ):
        if re.search(rule["pattern_regex"], normalized):
            return str(rule["subniche"])
    return None

from __future__ import annotations

import json
from typing import Any

# Contrato operacional minimo para o catalogo curado consumido pelo fluxo:
# collector -> scorer -> selecao -> copy -> dispatch.
OPERATIONAL_CATALOG_FIELDNAMES = [
    "itemId",
    "productName",
    "productLink",
    "offerLink",
    "imageUrl",
    "price",
    "priceMax",
    "sales",
    "ratingStar",
    "shopType",
    "sellerCommissionRate",
    "shopeeCommissionRate",
    "subniches",
]


def project_operational_catalog_row(row: dict[str, Any]) -> dict[str, Any]:
    projected = {
        fieldname: row.get(fieldname)
        for fieldname in OPERATIONAL_CATALOG_FIELDNAMES
    }
    for fieldname in ("shopType", "subniches"):
        projected[fieldname] = _normalize_json_like_value(projected.get(fieldname))
    return projected


def _normalize_json_like_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized: Any = value
    while isinstance(normalized, str):
        text = normalized.strip()
        if not text:
            return text
        if not _looks_like_json_value(text):
            return text
        try:
            parsed = json.loads(text)
        except ValueError:
            return text
        if parsed == normalized:
            return parsed
        normalized = parsed
    return normalized


def _looks_like_json_value(value: str) -> bool:
    return (
        (value.startswith("[") and value.endswith("]"))
        or (value.startswith('"[') and value.endswith(']"'))
        or (value.startswith('"') and value.endswith('"'))
    )

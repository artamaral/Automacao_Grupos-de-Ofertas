from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ofertas_bot.models import CopyBrief
from ofertas_bot.storage.json_offer_store import offer_from_json, offer_to_json


class CopyBriefStoreError(ValueError):
    """Raised when local copy brief storage cannot parse saved data."""


class CopyBriefStoreWriteError(OSError):
    """Raised when local copy brief storage cannot write data."""


class JsonCopyBriefStore:
    """Optional local JSON storage for GPT copywriter input briefs."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, briefs: tuple[CopyBrief, ...]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = [copy_brief_to_json(brief) for brief in briefs]
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"Could not write copy briefs JSON to {self.path}"
            raise CopyBriefStoreWriteError(msg) from error

    def load(self) -> tuple[CopyBrief, ...]:
        if not self.path.exists():
            return ()

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            msg = "Saved copy briefs JSON is invalid"
            raise CopyBriefStoreError(msg) from error

        if not isinstance(payload, list):
            msg = "Saved copy briefs JSON must contain a list"
            raise CopyBriefStoreError(msg)

        return tuple(copy_brief_from_json(item) for item in payload)


def copy_brief_to_json(brief: CopyBrief) -> dict[str, Any]:
    offer = brief.offer
    return {
        "content_type": brief.content_type,
        "offer": offer_to_json(offer),
        "selection": {
            "score": brief.score,
            "reasons": list(brief.score_reasons),
        },
        "facts": {
            "title": offer.title,
            "marketplace": offer.marketplace.value,
            "niche": offer.niche,
            "url": offer.url,
            "item_id": offer.item_id,
            "image_url": offer.image_url,
            "price": offer.price,
            "old_price": offer.old_price,
            "discount_percent": offer.discount_percent,
            "sales_count": offer.sales_count,
            "rating": offer.rating,
            "commission_rate": offer.commission_rate,
            "is_prime_or_free_shipping": offer.is_prime_or_free_shipping,
            "shop_type_code": offer.shop_type_code,
        },
        "required_disclosures": list(brief.required_disclosures),
        "copy_constraints": list(brief.copy_constraints),
        "forbidden_claims": list(brief.forbidden_claims),
    }


def copy_brief_from_json(data: object) -> CopyBrief:
    if not isinstance(data, dict):
        msg = "Saved copy brief item must be an object"
        raise CopyBriefStoreError(msg)

    try:
        selection = data["selection"]
        if not isinstance(selection, dict):
            msg = "Saved copy brief selection must be an object"
            raise CopyBriefStoreError(msg)
        return CopyBrief(
            content_type=str(data["content_type"]),
            offer=offer_from_json(data["offer"]),
            score=float(selection["score"]),
            score_reasons=tuple(str(item) for item in selection.get("reasons", ())),
            required_disclosures=tuple(
                str(item) for item in data.get("required_disclosures", ())
            ),
            copy_constraints=tuple(str(item) for item in data.get("copy_constraints", ())),
            forbidden_claims=tuple(str(item) for item in data.get("forbidden_claims", ())),
        )
    except (KeyError, TypeError, ValueError) as error:
        msg = "Saved copy brief item is invalid"
        raise CopyBriefStoreError(msg) from error

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass


@dataclass(frozen=True)
class ShopeeAuthParams:
    partner_id: str
    secret_key: str
    path: str
    timestamp: int


class ShopeeSigner:
    """Creates deterministic HMAC signatures for Shopee API requests."""

    def sign(self, params: ShopeeAuthParams) -> str:
        base_string = f"{params.partner_id}{params.path}{params.timestamp}"
        return hmac.new(
            params.secret_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

from __future__ import annotations

import time
from dataclasses import dataclass

from ofertas_bot.providers.http import HttpRequest
from ofertas_bot.providers.shopee_auth import ShopeeAuthParams, ShopeeSigner


SHOPEE_SEARCH_PATH = "/api/v2/product/search_item"


@dataclass(frozen=True)
class ShopeeSearchRequestBuilder:
    partner_id: str
    secret_key: str
    base_url: str
    signer: ShopeeSigner = ShopeeSigner()

    def build(
        self,
        keyword: str,
        limit: int,
        timestamp: int | None = None,
    ) -> HttpRequest:
        request_timestamp = timestamp or int(time.time())
        sign = self.signer.sign(
            ShopeeAuthParams(
                partner_id=self.partner_id,
                secret_key=self.secret_key,
                path=SHOPEE_SEARCH_PATH,
                timestamp=request_timestamp,
            )
        )
        params = {
            "partner_id": self.partner_id,
            "timestamp": request_timestamp,
            "sign": sign,
            "keyword": keyword,
            "page_size": limit,
        }
        return HttpRequest(
            method="GET",
            url=f"{self.base_url}{SHOPEE_SEARCH_PATH}",
            params=params,
        )

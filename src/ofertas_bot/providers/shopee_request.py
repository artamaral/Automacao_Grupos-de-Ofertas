from __future__ import annotations

from time import time

from ofertas_bot.providers.http import HttpRequest
from ofertas_bot.providers.shopee_auth import ShopeeAuthParams, ShopeeSigner


SHOPEE_SEARCH_PATH = "/api/v2/product/search_item"


class ShopeeSearchRequestBuilder:
    def __init__(
        self,
        partner_id: str,
        secret_key: str,
        base_url: str,
        signer: ShopeeSigner | None = None,
    ) -> None:
        self.partner_id = partner_id
        self.secret_key = secret_key
        self.base_url = base_url
        self.signer = signer or ShopeeSigner()

    def build(
        self,
        keyword: str,
        limit: int,
        timestamp: int | None = None,
    ) -> HttpRequest:
        request_timestamp = timestamp or int(time())
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

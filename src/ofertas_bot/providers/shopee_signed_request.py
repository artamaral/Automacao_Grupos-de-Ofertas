import hashlib
import hmac
from dataclasses import dataclass

from ofertas_bot.providers.endpoints import SHOPEE_SEARCH_PATH
from ofertas_bot.providers.http import HttpRequest


@dataclass(frozen=True)
class ShopeeSignedRequestBuilder:
    partner_id: str
    api_credential: str
    base_url: str

    def build(
        self,
        keyword: str,
        limit: int,
        timestamp: int,
    ) -> HttpRequest:
        base_string = f"{self.partner_id}{SHOPEE_SEARCH_PATH}{timestamp}"
        signature = hmac.new(
            self.api_credential.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "sign": signature,
            "keyword": keyword,
            "page_size": limit,
        }
        return HttpRequest(
            method="GET",
            url=f"{self.base_url}{SHOPEE_SEARCH_PATH}",
            params=params,
        )

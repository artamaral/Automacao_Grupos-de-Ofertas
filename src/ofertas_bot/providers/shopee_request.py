SHOPEE_SEARCH_PATH = "/api/v2/product/search_item"


class BuiltShopeeRequest:
    def __init__(self, method: str, url: str, params: dict[str, object]) -> None:
        self.method = method
        self.url = url
        self.params = params


class ShopeeSearchRequestBuilder:
    def __init__(self, partner_id: str, secret_key: str, base_url: str) -> None:
        self.partner_id = partner_id
        self.secret_key = secret_key
        self.base_url = base_url

    def build(
        self,
        keyword: str,
        limit: int,
        timestamp: int,
    ) -> BuiltShopeeRequest:
        import hashlib
        import hmac

        base_string = f"{self.partner_id}{SHOPEE_SEARCH_PATH}{timestamp}"
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
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
        return BuiltShopeeRequest(
            method="GET",
            url=f"{self.base_url}{SHOPEE_SEARCH_PATH}",
            params=params,
        )

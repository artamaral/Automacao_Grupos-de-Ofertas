from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

from ofertas_bot.providers.endpoints import SHOPEE_GRAPHQL_URL
from ofertas_bot.providers.gateway import execute_provider_request
from ofertas_bot.providers.http import ProviderHttpClient
from ofertas_bot.providers.retry import RetryPolicy, SystemSleeper
from ofertas_bot.providers.shopee_graphql import (
    ShopeeGraphqlSigner,
    build_graphql_request,
    extract_shopee_short_link,
    raise_if_graphql_errors,
)
from ofertas_bot.providers.transport import HttpTransport, UrllibHttpTransport
from ofertas_bot.settings import Settings

GENERATE_SHORT_LINK = """
mutation GenerateShortLink($originUrl: String, $subIds: [String]) {
  generateShortLink(input: {originUrl: $originUrl, subIds: $subIds}) { shortLink }
}
""".strip()

CONVERSION_REPORT = """
query DailyConversionReport($purchaseTimeStart: Int!, $purchaseTimeEnd: Int!, $scrollId: String) {
  conversionReport(
    purchaseTimeStart: $purchaseTimeStart, purchaseTimeEnd: $purchaseTimeEnd,
    conversionStatus: ALL, categoryType: ALL, orderStatus: ALL, buyerType: ALL,
    productType: ALL, fraudStatus: ALL, device: ALL, scrollId: $scrollId
  ) {
    nodes {
      clickTime purchaseTime conversionId shopeeCommissionCapped sellerCommission
      totalCommission netCommission mcnManagementFeeRate mcnManagementFee mcnContractId
      linkedMcnName buyerType utmContent device productType referrer
      orders {
        orderId shopType orderStatus
        items {
          shopId shopName completeTime promotionId modelId itemId itemName itemPrice
          displayItemStatus actualAmount refundAmount qty imageUrl itemTotalCommission
          itemSellerCommission itemSellerCommissionRate itemShopeeCommissionCapped
          itemShopeeCommissionRate itemNotes globalCategoryLv1Name globalCategoryLv2Name
          globalCategoryLv3Name fraudStatus fraudReason attributionType channelType
          campaignPartnerName campaignType
        }
      }
    }
    pageInfo { page limit hasNextPage scrollId }
  }
}
""".strip()


@dataclass
class ShopeeTrackingProvider:
    credential: str
    api_secret: str
    transport: HttpTransport = field(default_factory=UrllibHttpTransport)
    graphql_url: str = SHOPEE_GRAPHQL_URL
    http_client: ProviderHttpClient = field(default_factory=ProviderHttpClient)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    sleeper: SystemSleeper = field(default_factory=SystemSleeper)

    @classmethod
    def from_settings(cls, settings: Settings) -> ShopeeTrackingProvider:
        if not settings.enable_real_http:
            raise ValueError("ENABLE_REAL_HTTP must be true for Shopee tracking")
        if not settings.shopee_partner_id or not settings.shopee_secret_key:
            raise ValueError("SHOPEE_PARTNER_ID and SHOPEE_SECRET_KEY are required")
        return cls(settings.shopee_partner_id, settings.shopee_secret_key)

    def _execute(self, query: str, operation: str, variables: dict[str, Any]) -> dict[str, Any]:
        request = build_graphql_request(
            graphql_url=self.graphql_url,
            signer=ShopeeGraphqlSigner(self.credential, self.api_secret),
            timestamp=int(time()),
            query=query,
            operation_name=operation,
            variables=variables,
        )
        return execute_provider_request(
            request=request,
            transport=self.transport,
            http_client=self.http_client,
            provider_name="Shopee",
            retry_policy=self.retry_policy,
            sleeper=self.sleeper,
        )

    def generate_short_link(self, origin_url: str, sub_ids: list[str]) -> str:
        return extract_shopee_short_link(
            self._execute(GENERATE_SHORT_LINK, "GenerateShortLink", {
                "originUrl": origin_url,
                "subIds": sub_ids,
            })
        )

    def conversion_page(
        self, purchase_time_start: int, purchase_time_end: int, scroll_id: str | None = None
    ) -> dict[str, Any]:
        variables: dict[str, Any] = {
            "purchaseTimeStart": purchase_time_start,
            "purchaseTimeEnd": purchase_time_end,
        }
        if scroll_id is not None:
            variables["scrollId"] = scroll_id
        response = self._execute(CONVERSION_REPORT, "DailyConversionReport", variables)
        raise_if_graphql_errors(response)
        data = response.get("data")
        report = data.get("conversionReport") if isinstance(data, dict) else None
        if not isinstance(report, dict) or not isinstance(report.get("nodes"), list):
            raise ValueError("invalid conversionReport response")
        if not isinstance(report.get("pageInfo"), dict):
            raise ValueError("conversionReport.pageInfo is required")
        return report

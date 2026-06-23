from dataclasses import dataclass, field

from ofertas_bot.providers.endpoints import AMAZON_SEARCH_PATH
from ofertas_bot.providers.http import HttpRequest


@dataclass(frozen=True)
class AmazonSearchRequestBuilder:
    partner_tag: str
    base_url: str
    default_resources: tuple[str, ...] = field(
        default=(
            "Images.Primary.Medium",
            "ItemInfo.Title",
            "Offers.Listings.Price",
        )
    )

    def build(self, keyword: str, limit: int) -> HttpRequest:
        body = {
            "Keywords": keyword,
            "PartnerTag": self.partner_tag,
            "PartnerType": "Associates",
            "ItemCount": limit,
            "Resources": list(self.default_resources),
        }
        return HttpRequest(
            method="POST",
            url=f"{self.base_url}{AMAZON_SEARCH_PATH}",
            body=body,
        )

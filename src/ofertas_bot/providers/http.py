from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ProviderHttpError(RuntimeError):
    """Raised when an external provider HTTP response is not successful."""


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    data: dict[str, Any]

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code <= 299


class ProviderHttpClient:
    """Base HTTP client placeholder for marketplace integrations.

    The concrete network transport will be added when the real Shopee/Amazon
    integration is implemented. This class centralizes the response validation
    contract now, without making external calls yet.
    """

    def validate_response(self, response: HttpResponse, provider_name: str) -> dict[str, Any]:
        if response.ok:
            return response.data

        raise ProviderHttpError(
            f"{provider_name} request failed with status={response.status_code}"
        )

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ofertas_bot.providers.http import HttpRequest, HttpResponse


class HttpTransport(Protocol):
    def send(self, request: HttpRequest) -> HttpResponse:
        """Send an HTTP request and return a normalized response."""


@dataclass
class StaticHttpTransport:
    response: HttpResponse
    requests: list[HttpRequest] = field(default_factory=list)

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return self.response

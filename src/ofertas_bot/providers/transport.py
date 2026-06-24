from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ofertas_bot.providers.http import HttpRequest, HttpResponse


class HttpTransportError(RuntimeError):
    """Raised when an HTTP transport cannot complete a request."""


class HttpTransport(Protocol):
    def send(self, request: HttpRequest) -> HttpResponse:
        """Send an HTTP request and return a normalized response."""


def encode_json_body(body: dict[str, Any]) -> bytes:
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@dataclass
class StaticHttpTransport:
    response: HttpResponse
    requests: list[HttpRequest] = field(default_factory=list)

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return self.response


@dataclass(frozen=True)
class UrllibHttpTransport:
    timeout_seconds: float = 10.0
    opener: Callable[..., Any] = urlopen

    def send(self, request: HttpRequest) -> HttpResponse:
        prepared_request = self._build_request(request)
        try:
            with self.opener(prepared_request, timeout=self.timeout_seconds) as response:
                status_code = self._status_code(response)
                data = self._read_json(response.read())
                return HttpResponse(status_code=status_code, data=data)
        except HTTPError as error:
            return HttpResponse(status_code=error.code, data=self._read_json(error.read()))
        except URLError as error:
            msg = "HTTP transport request failed"
            raise HttpTransportError(msg) from error

    def _build_request(self, request: HttpRequest) -> Request:
        url = self._build_url(request)
        body = self._encode_body(request.body)
        headers = dict(request.headers)
        if body is not None:
            headers.setdefault("Content-Type", "application/json")

        return Request(
            url=url,
            data=body,
            headers=headers,
            method=request.method.upper(),
        )

    def _build_url(self, request: HttpRequest) -> str:
        if not request.params:
            return request.url

        separator = "&" if "?" in request.url else "?"
        return f"{request.url}{separator}{urlencode(request.params, doseq=True)}"

    def _encode_body(self, body: dict[str, Any] | None) -> bytes | None:
        if body is None:
            return None
        return encode_json_body(body)

    def _read_json(self, raw_body: bytes) -> dict[str, Any]:
        if not raw_body:
            return {}
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as error:
            msg = "HTTP transport response is not valid JSON"
            raise HttpTransportError(msg) from error

        if not isinstance(data, dict):
            msg = "HTTP transport response JSON must be an object"
            raise HttpTransportError(msg)
        return data

    def _status_code(self, response: Any) -> int:
        status = getattr(response, "status", None)
        if isinstance(status, int):
            return status
        return int(response.getcode())

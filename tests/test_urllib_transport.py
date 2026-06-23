import pytest
from urllib.error import URLError

from ofertas_bot.providers.http import HttpRequest
from ofertas_bot.providers.transport import HttpTransportError, UrllibHttpTransport


class FakeUrlResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class RecordingOpener:
    def __init__(self, response: FakeUrlResponse) -> None:
        self.response = response
        self.requests = []
        self.timeouts = []

    def __call__(self, request, timeout: float):
        self.requests.append(request)
        self.timeouts.append(timeout)
        return self.response


def test_urllib_http_transport_sends_get_with_query_params() -> None:
    opener = RecordingOpener(FakeUrlResponse(status=200, body=b'{"items": []}'))
    transport = UrllibHttpTransport(timeout_seconds=3.0, opener=opener)
    request = HttpRequest(
        method="GET",
        url="https://example.com/search",
        params={"q": "maquiagem", "limit": 10},
    )

    response = transport.send(request)

    assert response.status_code == 200
    assert response.data == {"items": []}
    assert opener.timeouts == [3.0]
    assert opener.requests[0].full_url == "https://example.com/search?q=maquiagem&limit=10"
    assert opener.requests[0].get_method() == "GET"


def test_urllib_http_transport_sends_json_body() -> None:
    opener = RecordingOpener(FakeUrlResponse(status=200, body=b'{"ok": true}'))
    transport = UrllibHttpTransport(opener=opener)
    request = HttpRequest(
        method="POST",
        url="https://example.com/search",
        body={"keyword": "maquiagem"},
    )

    response = transport.send(request)

    assert response.data == {"ok": True}
    assert opener.requests[0].data == b'{"keyword": "maquiagem"}'
    assert opener.requests[0].get_header("Content-type") == "application/json"
    assert opener.requests[0].get_method() == "POST"


def test_urllib_http_transport_rejects_invalid_json() -> None:
    opener = RecordingOpener(FakeUrlResponse(status=200, body=b'not-json'))
    transport = UrllibHttpTransport(opener=opener)

    with pytest.raises(HttpTransportError, match="not valid JSON"):
        transport.send(HttpRequest(method="GET", url="https://example.com"))


def test_urllib_http_transport_wraps_url_error() -> None:
    def failing_opener(request, timeout: float):
        raise URLError("network down")

    transport = UrllibHttpTransport(opener=failing_opener)

    with pytest.raises(HttpTransportError, match="request failed"):
        transport.send(HttpRequest(method="GET", url="https://example.com"))

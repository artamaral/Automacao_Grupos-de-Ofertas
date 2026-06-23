from ofertas_bot.providers.http import HttpRequest, HttpResponse
from ofertas_bot.providers.transport import StaticHttpTransport


def test_static_http_transport_records_request_and_returns_response() -> None:
    request = HttpRequest(method="GET", url="https://example.com", params={"q": "maquiagem"})
    response = HttpResponse(status_code=200, data={"items": []})
    transport = StaticHttpTransport(response=response)

    result = transport.send(request)

    assert result == response
    assert transport.requests == [request]

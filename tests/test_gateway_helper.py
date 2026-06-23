import pytest

from ofertas_bot.providers.gateway import execute_provider_request
from ofertas_bot.providers.http import HttpRequest, HttpResponse, ProviderHttpClient, ProviderHttpError
from ofertas_bot.providers.transport import StaticHttpTransport


def test_execute_provider_request_returns_validated_payload() -> None:
    request = HttpRequest(method="GET", url="https://example.com/search")
    response = HttpResponse(status_code=200, data={"items": []})
    transport = StaticHttpTransport(response=response)

    payload = execute_provider_request(
        request=request,
        transport=transport,
        http_client=ProviderHttpClient(),
        provider_name="Teste",
    )

    assert payload == {"items": []}
    assert transport.requests == [request]


def test_execute_provider_request_requires_transport() -> None:
    request = HttpRequest(method="GET", url="https://example.com/search")

    with pytest.raises(RuntimeError, match="Teste gateway transport is not configured"):
        execute_provider_request(
            request=request,
            transport=None,
            http_client=ProviderHttpClient(),
            provider_name="Teste",
        )


def test_execute_provider_request_raises_provider_http_error() -> None:
    request = HttpRequest(method="GET", url="https://example.com/search")
    response = HttpResponse(status_code=500, data={"error": "unavailable"})
    transport = StaticHttpTransport(response=response)

    with pytest.raises(ProviderHttpError, match="Teste request failed with status=500"):
        execute_provider_request(
            request=request,
            transport=transport,
            http_client=ProviderHttpClient(),
            provider_name="Teste",
        )

import pytest

from ofertas_bot.providers.http import HttpResponse, ProviderHttpClient, ProviderHttpError


def test_http_client_returns_data_when_response_is_ok() -> None:
    client = ProviderHttpClient()
    response = HttpResponse(status_code=200, data={"items": []})

    data = client.validate_response(response=response, provider_name="provider")

    assert data == {"items": []}


def test_http_client_raises_when_response_is_not_ok() -> None:
    client = ProviderHttpClient()
    response = HttpResponse(status_code=500, data={})

    with pytest.raises(ProviderHttpError):
        client.validate_response(response=response, provider_name="provider")

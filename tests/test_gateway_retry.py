from dataclasses import dataclass, field

import pytest

from ofertas_bot.providers.gateway import execute_provider_request
from ofertas_bot.providers.http import HttpRequest, HttpResponse, ProviderHttpClient, ProviderHttpError
from ofertas_bot.providers.retry import RetryPolicy


@dataclass
class SequentialTransport:
    responses: list[HttpResponse]
    requests: list[HttpRequest] = field(default_factory=list)

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return self.responses.pop(0)


@dataclass
class RecordingSleeper:
    delays: list[float] = field(default_factory=list)

    def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


def test_execute_provider_request_retries_then_returns_success() -> None:
    request = HttpRequest(method="GET", url="https://example.com/search")
    transport = SequentialTransport(
        responses=[
            HttpResponse(status_code=429, data={"error": "rate limit"}),
            HttpResponse(status_code=200, data={"items": []}),
        ]
    )
    sleeper = RecordingSleeper()

    payload = execute_provider_request(
        request=request,
        transport=transport,
        http_client=ProviderHttpClient(),
        provider_name="Teste",
        retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=1.0),
        sleeper=sleeper,
    )

    assert payload == {"items": []}
    assert transport.requests == [request, request]
    assert sleeper.delays == [1.0]


def test_execute_provider_request_raises_after_retry_exhaustion() -> None:
    request = HttpRequest(method="GET", url="https://example.com/search")
    transport = SequentialTransport(
        responses=[
            HttpResponse(status_code=429, data={"error": "rate limit"}),
            HttpResponse(status_code=429, data={"error": "rate limit"}),
        ]
    )
    sleeper = RecordingSleeper()

    with pytest.raises(ProviderHttpError, match="Teste request failed with status=429"):
        execute_provider_request(
            request=request,
            transport=transport,
            http_client=ProviderHttpClient(),
            provider_name="Teste",
            retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=1.0),
            sleeper=sleeper,
        )

    assert transport.requests == [request, request]
    assert sleeper.delays == [1.0]

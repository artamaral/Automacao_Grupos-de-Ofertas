from typing import Any

from ofertas_bot.providers.http import HttpRequest, ProviderHttpClient
from ofertas_bot.providers.retry import NoOpSleeper, RetryPolicy, Sleeper
from ofertas_bot.providers.transport import HttpTransport


class ProviderLimitError(ValueError):
    """Raised when a provider receives an invalid limit."""


def validate_positive_limit(limit: int) -> None:
    if limit <= 0:
        msg = f"Provider limit must be greater than zero. Received: {limit}"
        raise ProviderLimitError(msg)


def execute_provider_request(
    *,
    request: HttpRequest,
    transport: HttpTransport | None,
    http_client: ProviderHttpClient,
    provider_name: str,
    retry_policy: RetryPolicy | None = None,
    sleeper: Sleeper | None = None,
) -> dict[str, Any]:
    if transport is None:
        msg = f"{provider_name} gateway transport is not configured"
        raise RuntimeError(msg)

    active_sleeper = sleeper or NoOpSleeper()
    attempt = 1

    while True:
        response = transport.send(request)
        if retry_policy is None or not retry_policy.should_retry(
            status_code=response.status_code,
            attempt=attempt,
        ):
            return http_client.validate_response(response, provider_name=provider_name)

        active_sleeper.sleep(retry_policy.delay_for_attempt(attempt))
        attempt += 1

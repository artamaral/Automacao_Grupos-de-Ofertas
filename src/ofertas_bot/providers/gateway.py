from typing import Any

from ofertas_bot.providers.http import HttpRequest, ProviderHttpClient
from ofertas_bot.providers.transport import HttpTransport


def execute_provider_request(
    *,
    request: HttpRequest,
    transport: HttpTransport | None,
    http_client: ProviderHttpClient,
    provider_name: str,
) -> dict[str, Any]:
    if transport is None:
        msg = f"{provider_name} gateway transport is not configured"
        raise RuntimeError(msg)

    response = transport.send(request)
    return http_client.validate_response(response, provider_name=provider_name)

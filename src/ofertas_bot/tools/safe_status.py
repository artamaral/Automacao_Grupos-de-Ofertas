from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ofertas_bot.models import Marketplace
from ofertas_bot.providers.amazon import AmazonProvider
from ofertas_bot.providers.provider_settings import (
    DEFAULT_PROVIDER_BASE_URL,
    get_provider_base_urls,
    get_provider_path_confirmations,
    get_provider_paths,
)
from ofertas_bot.providers.real_http_guard import RealHttpValidationError
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.settings import Settings, get_settings

REAL_MARKETPLACES = (Marketplace.SHOPEE.value, Marketplace.AMAZON.value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mostra status seguro para HTTP real")
    parser.add_argument(
        "--marketplace",
        choices=REAL_MARKETPLACES,
        required=True,
        help="Marketplace real para validar",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    marketplace = Marketplace(args.marketplace)
    settings = get_settings()

    print("INFO | Status seguro do ambiente")
    print(f"INFO | marketplace={marketplace.value}")
    print(f"INFO | enable_real_http={_format_bool(settings.enable_real_http)}")
    print(f"INFO | enable_real_publish={_format_bool(settings.enable_real_publish)}")
    print(f"INFO | default_dry_run={_format_bool(settings.default_dry_run)}")

    blocked_reasons = _collect_blocked_reasons(marketplace=marketplace, settings=settings)

    if blocked_reasons:
        print("ERRO | Ambiente bloqueado para chamada real", file=sys.stderr)
        for reason in blocked_reasons:
            print(f"DETALHE | {reason}", file=sys.stderr)
        print("AÇÃO | Revise o checklist operacional pré-chamada real.", file=sys.stderr)
        return 3

    print("INFO | Ambiente pronto para chamada real controlada")
    print("INFO | Publicação real continua fora do escopo deste status.")
    return 0


def _collect_blocked_reasons(marketplace: Marketplace, settings: Settings) -> list[str]:
    blocked_reasons: list[str] = []

    if settings.enable_real_publish:
        blocked_reasons.append("publicação real habilitada")

    blocked_reasons.extend(_collect_provider_readiness_errors(marketplace, settings))
    blocked_reasons.extend(_collect_path_status_errors(marketplace))

    return blocked_reasons


def _collect_provider_readiness_errors(
    marketplace: Marketplace,
    settings: Settings,
) -> list[str]:
    try:
        if marketplace == Marketplace.SHOPEE:
            ShopeeProvider(settings=settings).validate_real_http_ready()
        elif marketplace == Marketplace.AMAZON:
            AmazonProvider(settings=settings).validate_real_http_ready()
    except RealHttpValidationError as error:
        return [str(error)]

    return []


def _collect_path_status_errors(marketplace: Marketplace) -> list[str]:
    base_urls = get_provider_base_urls()
    paths = get_provider_paths()
    confirmations = get_provider_path_confirmations()

    if marketplace == Marketplace.SHOPEE:
        print(f"INFO | base_url={_format_base_url(base_urls.shopee)}")
        print(f"INFO | search_path={paths.shopee_search}")
        print(
            "INFO | search_path_confirmed="
            f"{_format_bool(confirmations.shopee_search)}"
        )
        if not confirmations.shopee_search:
            return ["endpoint da Shopee não confirmado"]
        return []

    print(f"INFO | base_url={_format_base_url(base_urls.amazon)}")
    print(f"INFO | search_path={paths.amazon_search}")
    return []


def _format_base_url(value: str) -> str:
    if value == DEFAULT_PROVIDER_BASE_URL:
        return "<placeholder>"
    return value


def _format_bool(value: bool) -> str:
    return "true" if value else "false"


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

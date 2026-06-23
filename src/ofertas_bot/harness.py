from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ofertas_bot.agents.collector import CollectorAgent
from ofertas_bot.agents.compliance import ComplianceAgent
from ofertas_bot.agents.copywriter import CopywriterAgent
from ofertas_bot.agents.publisher import DryRunPublisher
from ofertas_bot.agents.scorer import ScorerAgent
from ofertas_bot.models import Marketplace
from ofertas_bot.providers.amazon import AmazonConfigurationError
from ofertas_bot.providers.amazon_gateway import AmazonPayloadError
from ofertas_bot.providers.http import ProviderHttpError
from ofertas_bot.providers.shopee import ShopeeConfigurationError
from ofertas_bot.providers.shopee_gateway import ShopeePayloadError
from ofertas_bot.providers.transport import HttpTransportError
from ofertas_bot.settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harness dry-run do bot de ofertas")
    parser.add_argument(
        "--niche",
        required=True,
        help="Nicho do grupo, ex: maquiagem, pesca, casa",
    )
    parser.add_argument(
        "--marketplace",
        choices=[item.value for item in Marketplace],
        default=Marketplace.MOCK.value,
        help="Marketplace para simular/buscar",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Quantidade máxima de ofertas",
    )
    parser.add_argument(
        "--target",
        default="grupo-vip-dry-run",
        help="Destino lógico da publicação",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Simula publicação",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    settings = get_settings()
    args = build_parser().parse_args(argv)

    marketplace = Marketplace(args.marketplace)
    limit = args.limit or settings.max_offers_per_run
    dry_run = bool(args.dry_run or settings.default_dry_run)

    collector = CollectorAgent()
    scorer = ScorerAgent()
    copywriter = CopywriterAgent()
    compliance = ComplianceAgent(settings=settings)
    publisher = DryRunPublisher()

    try:
        offers = collector.collect(marketplace=marketplace, niche=args.niche, limit=limit)
    except ShopeeConfigurationError as error:
        return _print_configuration_error(marketplace=Marketplace.SHOPEE, error=error)
    except AmazonConfigurationError as error:
        return _print_configuration_error(marketplace=Marketplace.AMAZON, error=error)
    except ShopeePayloadError as error:
        return _print_payload_error(marketplace=Marketplace.SHOPEE, error=error)
    except AmazonPayloadError as error:
        return _print_payload_error(marketplace=Marketplace.AMAZON, error=error)
    except ProviderHttpError as error:
        return _print_provider_http_error(marketplace=marketplace, error=error)
    except HttpTransportError as error:
        return _print_transport_error(marketplace=marketplace, error=error)

    scored_offers = scorer.score(offers)

    print(
        f"INFO | Encontradas {len(scored_offers)} ofertas "
        f"para nicho={args.niche} marketplace={marketplace}"
    )

    for index, scored in enumerate(scored_offers, start=1):
        draft = copywriter.create_message(scored)
        result = compliance.validate(draft=draft, dry_run=dry_run)

        print("-" * 80)
        print(f"INFO | Oferta #{index} score={scored.score} aprovado={result.approved}")
        if result.reasons:
            print("WARN | Bloqueios:", "; ".join(result.reasons))
            continue

        publish_result = publisher.publish(draft=draft, target=args.target)
        print(publish_result.message)
        print(
            f"INFO | dry_run={publish_result.dry_run} "
            f"sent={publish_result.sent} target={publish_result.target}"
        )

    return 0


def _print_configuration_error(marketplace: Marketplace, error: Exception) -> int:
    marketplace_name = marketplace.value.capitalize()
    print(f"ERRO | Configuração da {marketplace_name} incompleta", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Configure o arquivo .env local ou rode com --marketplace mock.",
        file=sys.stderr,
    )
    return 2


def _print_payload_error(marketplace: Marketplace, error: Exception) -> int:
    marketplace_name = marketplace.value.capitalize()
    print(f"ERRO | Resposta da {marketplace_name} em formato inesperado", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Valide o payload retornado pelo provider antes de publicar ofertas.",
        file=sys.stderr,
    )
    return 3


def _print_provider_http_error(marketplace: Marketplace, error: Exception) -> int:
    marketplace_name = marketplace.value.capitalize()
    print(f"ERRO | Falha na resposta HTTP da {marketplace_name}", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Verifique status, rate limit e disponibilidade antes de nova tentativa.",
        file=sys.stderr,
    )
    return 3


def _print_transport_error(marketplace: Marketplace, error: Exception) -> int:
    marketplace_name = marketplace.value.capitalize()
    print(f"ERRO | Falha de transporte HTTP da {marketplace_name}", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print(
        "AÇÃO | Verifique conexão, timeout e configuração antes de nova tentativa.",
        file=sys.stderr,
    )
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

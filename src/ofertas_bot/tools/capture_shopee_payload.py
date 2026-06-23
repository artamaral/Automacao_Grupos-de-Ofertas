from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ofertas_bot.providers.payload_anonymizer import anonymize_payload
from ofertas_bot.providers.provider_settings import get_provider_path_confirmations
from ofertas_bot.providers.real_http_guard import RealHttpValidationError
from ofertas_bot.providers.shopee import ShopeeProvider
from ofertas_bot.settings import get_settings

DEFAULT_OUTPUT_PATH = Path("tmp/shopee-real-anonymized.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Captura uma resposta real da Shopee já anonimizada"
    )
    parser.add_argument("--niche", required=True, help="Termo de busca para a chamada controlada")
    parser.add_argument("--limit", type=int, default=1, help="Quantidade máxima solicitada")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Arquivo de saída dentro de tmp/",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path = _validate_output_path(args.output)

    if not get_provider_path_confirmations().shopee_search:
        print("ERRO | Endpoint da Shopee não confirmado", file=sys.stderr)
        print("AÇÃO | Revise o preview seguro antes de capturar payload.", file=sys.stderr)
        return 3

    provider = ShopeeProvider(settings=get_settings())

    try:
        response_data = provider.fetch_raw_response(niche=args.niche, limit=args.limit)
    except RealHttpValidationError as error:
        print("ERRO | HTTP real bloqueado por configuração insegura", file=sys.stderr)
        print(f"DETALHE | {error}", file=sys.stderr)
        return 3

    anonymized_payload = anonymize_payload(response_data)
    _write_json(output_path=output_path, payload=anonymized_payload)

    print("INFO | Resposta real anonimizada salva")
    print(f"INFO | output={output_path.as_posix()}")
    print("INFO | Nenhum payload bruto foi salvo automaticamente.")
    print("INFO | Nenhuma publicação foi executada.")
    return 0


def _validate_output_path(output_path: Path) -> Path:
    normalized_path = output_path.as_posix()
    if not normalized_path.startswith("tmp/"):
        raise SystemExit("ERRO | O arquivo de saída deve ficar dentro de tmp/")
    return output_path


def _write_json(output_path: Path, payload: Any) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

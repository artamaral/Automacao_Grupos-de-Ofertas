from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.providers.payload_anonymizer import anonymize_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Anonimiza payload JSON local")
    parser.add_argument("--input", required=True, help="Caminho do JSON bruto local")
    parser.add_argument("--output", required=True, help="Caminho do JSON anonimizado")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)

    if input_path.resolve() == output_path.resolve():
        print("ERRO | Entrada e saída não podem ser o mesmo arquivo", file=sys.stderr)
        print("AÇÃO | Use um caminho separado para o JSON anonimizado.", file=sys.stderr)
        return 3

    try:
        raw_payload = json.loads(input_path.read_text(encoding="utf-8"))
    except OSError as error:
        print("ERRO | Não foi possível ler o JSON bruto", file=sys.stderr)
        print(f"DETALHE | {error}", file=sys.stderr)
        return 3
    except json.JSONDecodeError as error:
        print("ERRO | JSON bruto inválido", file=sys.stderr)
        print(f"DETALHE | {error}", file=sys.stderr)
        return 3

    anonymized_payload = anonymize_payload(raw_payload)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(anonymized_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        print("ERRO | Não foi possível salvar o JSON anonimizado", file=sys.stderr)
        print(f"DETALHE | {error}", file=sys.stderr)
        return 3

    print(f"INFO | Payload anonimizado salvo em {output_path}")
    print("INFO | Revise manualmente antes de commitar qualquer fixture.")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

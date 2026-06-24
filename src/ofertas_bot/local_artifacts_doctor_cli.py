from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verifica artefatos JSON locais do fluxo")
    parser.add_argument("--queue-json", required=True, help="Caminho de review_queue.json")
    parser.add_argument("--approved-json", required=True, help="Caminho de approved_messages.json")
    parser.add_argument("--manifest-json", required=True, help="Caminho do manifesto local")
    parser.add_argument(
        "--bundle-json",
        default=None,
        help="Caminho opcional do relatório consolidado local",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        queue_items = _load_json_list(Path(args.queue_json))
        approved_items = _load_json_list(Path(args.approved_json))
        manifest_items = _load_json_list(Path(args.manifest_json))
        bundle_payload = _load_json_object(Path(args.bundle_json)) if args.bundle_json else None
    except ValueError as error:
        return _print_doctor_error(error=error)

    queue_status = _status_counts(queue_items)
    manifest_status = _status_counts(manifest_items)
    issues = _find_issues(
        queue_status=queue_status,
        approved_items=approved_items,
        manifest_items=manifest_items,
        manifest_status=manifest_status,
        bundle_payload=bundle_payload,
    )

    print(f"INFO | Fila total: {len(queue_items)}")
    print(f"INFO | Fila pendente: {queue_status.get('pending', 0)}")
    print(f"INFO | Fila aprovada: {queue_status.get('approved', 0)}")
    print(f"INFO | Fila rejeitada: {queue_status.get('rejected', 0)}")
    print(f"INFO | Mensagens aprovadas exportadas: {len(approved_items)}")
    print(f"INFO | Manifesto total: {len(manifest_items)}")
    print(f"INFO | Manifesto ready: {manifest_status.get('ready', 0)}")
    if bundle_payload is not None:
        print(f"INFO | Bundle válido: {bundle_payload.get('valid', False)}")

    if issues:
        print("ERRO | Doctor local encontrou problemas.", file=sys.stderr)
        for issue in issues:
            print(f"DETALHE | {issue}", file=sys.stderr)
        print("AÇÃO | Corrija os artefatos locais antes de seguir.", file=sys.stderr)
        return 3

    print("INFO | Doctor local aprovado.")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        msg = f"{path} deve conter uma lista"
        raise ValueError(msg)

    items: list[dict[str, Any]] = []
    for raw_item in payload:
        if not isinstance(raw_item, dict):
            msg = f"{path} contém item que não é objeto"
            raise ValueError(msg)
        items.append(raw_item)
    return items


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        msg = f"{path} deve conter um objeto"
        raise ValueError(msg)
    return payload


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        msg = f"Não foi possível ler {path}"
        raise ValueError(msg) from error
    except json.JSONDecodeError as error:
        msg = f"{path} não contém JSON válido"
        raise ValueError(msg) from error


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(item.get("status", "unknown")) for item in items)
    return dict(sorted(counts.items()))


def _find_issues(
    *,
    queue_status: dict[str, int],
    approved_items: list[dict[str, Any]],
    manifest_items: list[dict[str, Any]],
    manifest_status: dict[str, int],
    bundle_payload: dict[str, Any] | None,
) -> list[str]:
    issues: list[str] = []

    if queue_status.get("pending", 0) > 0:
        issues.append("fila ainda possui itens pendentes")
    if queue_status.get("approved", 0) == 0:
        issues.append("fila sem itens aprovados")
    if not approved_items:
        issues.append("arquivo de aprovadas vazio")
    if not manifest_items:
        issues.append("manifesto local vazio")
    if manifest_status.get("ready", 0) != len(manifest_items):
        issues.append("manifesto possui item fora do status ready")
    if manifest_items and len(manifest_items) != len(approved_items):
        issues.append("manifesto e aprovadas possuem totais diferentes")
    if bundle_payload is not None and bundle_payload.get("valid") is not True:
        issues.append("bundle local não está válido")

    return issues


def _print_doctor_error(error: Exception) -> int:
    print("ERRO | Não foi possível executar doctor local", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminhos e formatos dos arquivos locais.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

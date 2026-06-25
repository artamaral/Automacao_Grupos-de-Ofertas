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
        "--dispatch-artifact-json",
        default=None,
        help="Caminho opcional do artefato local de disparo",
    )
    parser.add_argument(
        "--dispatch-report-json",
        default=None,
        help="Caminho opcional do relatorio local de disparo",
    )
    parser.add_argument(
        "--bundle-json",
        default=None,
        help="Caminho opcional do relatorio consolidado local",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        queue_items = _load_json_list(Path(args.queue_json))
        approved_items = _load_json_list(Path(args.approved_json))
        manifest_items = _load_json_list(Path(args.manifest_json))
        dispatch_artifact_payload = (
            _load_json_object(Path(args.dispatch_artifact_json))
            if args.dispatch_artifact_json
            else None
        )
        dispatch_report_payload = (
            _load_json_object(Path(args.dispatch_report_json))
            if args.dispatch_report_json
            else None
        )
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
        dispatch_artifact_payload=dispatch_artifact_payload,
        dispatch_report_payload=dispatch_report_payload,
        bundle_payload=bundle_payload,
    )

    print(f"INFO | Fila total: {len(queue_items)}")
    print(f"INFO | Fila pendente: {queue_status.get('pending', 0)}")
    print(f"INFO | Fila aprovada: {queue_status.get('approved', 0)}")
    print(f"INFO | Fila rejeitada: {queue_status.get('rejected', 0)}")
    print(f"INFO | Mensagens aprovadas exportadas: {len(approved_items)}")
    print(f"INFO | Manifesto total: {len(manifest_items)}")
    print(f"INFO | Manifesto ready: {manifest_status.get('ready', 0)}")
    if dispatch_artifact_payload is not None:
        print(
            "INFO | Dispatch artifact mensagens disponiveis: "
            f"{_summary_int(dispatch_artifact_payload, 'total_available_messages')}"
        )
    if dispatch_report_payload is not None:
        print(
            "INFO | Dispatch report mensagens: "
            f"{_summary_int(dispatch_report_payload, 'total_messages')}"
        )
    if bundle_payload is not None:
        print(f"INFO | Bundle valido: {bundle_payload.get('valid', False)}")

    if issues:
        print("ERRO | Doctor local encontrou problemas.", file=sys.stderr)
        for issue in issues:
            print(f"DETALHE | {issue}", file=sys.stderr)
        print("ACAO | Corrija os artefatos locais antes de seguir.", file=sys.stderr)
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
            msg = f"{path} contem item que nao e objeto"
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
        msg = f"Nao foi possivel ler {path}"
        raise ValueError(msg) from error
    except json.JSONDecodeError as error:
        msg = f"{path} nao contem JSON valido"
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
    dispatch_artifact_payload: dict[str, Any] | None,
    dispatch_report_payload: dict[str, Any] | None,
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
    if dispatch_artifact_payload is not None:
        if _summary_int(dispatch_artifact_payload, "total_available_messages") != len(
            manifest_items
        ):
            issues.append("dispatch artifact diverge do total do manifesto")
    if dispatch_artifact_payload is not None and dispatch_report_payload is not None:
        if _summary_int(dispatch_artifact_payload, "total_selected_messages") != _summary_int(
            dispatch_report_payload, "total_messages"
        ):
            issues.append("dispatch artifact e dispatch report possuem totais diferentes")
        if str(dispatch_report_payload.get("source_generated_at", "")) != str(
            dispatch_artifact_payload.get("generated_at", "")
        ):
            issues.append("dispatch report referencia artifact diferente")
    if bundle_payload is not None and bundle_payload.get("valid") is not True:
        issues.append("bundle local nao esta valido")

    return issues


def _summary_int(payload: dict[str, Any], key: str) -> int:
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        return 0
    return int(summary.get(key, 0))


def _print_doctor_error(error: Exception) -> int:
    print("ERRO | Nao foi possivel executar doctor local", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("ACAO | Verifique caminhos e formatos dos arquivos locais.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

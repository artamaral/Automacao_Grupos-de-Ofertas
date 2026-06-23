from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Consolida revisão local em um relatório JSON")
    parser.add_argument(
        "--queue-json",
        required=True,
        help="Caminho do arquivo local review_queue.json",
    )
    parser.add_argument(
        "--approved-messages-json",
        required=True,
        help="Caminho do arquivo local approved_messages.json",
    )
    parser.add_argument(
        "--manifest-json",
        required=True,
        help="Caminho do arquivo local de manifesto",
    )
    parser.add_argument(
        "--save-bundle-json",
        required=True,
        help="Caminho local para salvar o relatório consolidado",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        queue_file = _load_json_file(Path(args.queue_json))
        approved_file = _load_json_file(Path(args.approved_messages_json))
        manifest_file = _load_json_file(Path(args.manifest_json))
        report = _build_bundle_report(
            queue_file=queue_file,
            approved_file=approved_file,
            manifest_file=manifest_file,
        )
        output_path = Path(args.save_bundle_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
    except (OSError, ValueError) as error:
        return _print_bundle_error(error=error)

    print(f"INFO | Relatório consolidado salvo em {output_path}")
    print(f"INFO | Fila pendente: {report['checks']['queue_pending']}")
    print(f"INFO | Mensagens aprovadas: {report['checks']['approved_messages']}")
    print(f"INFO | Itens prontos no manifesto: {report['checks']['manifest_ready']}")
    print(f"INFO | Válido: {report['valid']}")
    print("INFO | Nenhum envio foi executado.")
    return 0 if report["valid"] else 3


def _load_json_file(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    try:
        payload = json.loads(content.decode("utf-8"))
    except UnicodeDecodeError as error:
        msg = f"{path} não está em UTF-8"
        raise ValueError(msg) from error
    except json.JSONDecodeError as error:
        msg = f"{path} não contém JSON válido"
        raise ValueError(msg) from error

    if not isinstance(payload, list):
        msg = f"{path} deve conter uma lista"
        raise ValueError(msg)

    for raw_item in payload:
        if not isinstance(raw_item, dict):
            msg = f"{path} contém item que não é objeto"
            raise ValueError(msg)

    return {
        "path": str(path),
        "content": content,
        "items": payload,
    }


def _build_bundle_report(
    queue_file: dict[str, Any],
    approved_file: dict[str, Any],
    manifest_file: dict[str, Any],
) -> dict[str, Any]:
    queue_items = _items(queue_file)
    approved_items = _items(approved_file)
    manifest_items = _items(manifest_file)
    queue_status_counts = _status_counts(queue_items)
    manifest_status_counts = _status_counts(manifest_items)
    issues = _find_issues(
        queue_status_counts=queue_status_counts,
        approved_items=approved_items,
        manifest_items=manifest_items,
        manifest_status_counts=manifest_status_counts,
    )
    return {
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "files": {
            "queue": _file_report(queue_file, queue_status_counts),
            "approved_messages": _file_report(approved_file, _status_counts(approved_items)),
            "manifest": _file_report(manifest_file, manifest_status_counts),
        },
        "checks": {
            "queue_pending": queue_status_counts.get("pending", 0),
            "approved_messages": len(approved_items),
            "manifest_items": len(manifest_items),
            "manifest_ready": manifest_status_counts.get("ready", 0),
        },
        "valid": not issues,
        "issues": issues,
    }


def _items(file_data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(file_data["items"])


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(item.get("status", "unknown")) for item in items)
    return dict(sorted(counts.items()))


def _file_report(file_data: dict[str, Any], status_counts: dict[str, int]) -> dict[str, Any]:
    content = bytes(file_data["content"])
    return {
        "path": file_data["path"],
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "items": len(_items(file_data)),
        "status_counts": status_counts,
    }


def _find_issues(
    *,
    queue_status_counts: dict[str, int],
    approved_items: list[dict[str, Any]],
    manifest_items: list[dict[str, Any]],
    manifest_status_counts: dict[str, int],
) -> list[str]:
    issues: list[str] = []
    if queue_status_counts.get("pending", 0) > 0:
        issues.append("fila ainda possui itens pendentes")
    if not approved_items:
        issues.append("nenhuma mensagem aprovada exportada")
    if not manifest_items:
        issues.append("manifesto vazio")
    if manifest_status_counts.get("ready", 0) != len(manifest_items):
        issues.append("manifesto possui item fora do status ready")
    if manifest_items and len(manifest_items) != len(approved_items):
        issues.append("total do manifesto difere do total de aprovadas")
    return issues


def _print_bundle_error(error: Exception) -> int:
    print("ERRO | Não foi possível consolidar revisão local", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminhos e formato dos arquivos locais.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

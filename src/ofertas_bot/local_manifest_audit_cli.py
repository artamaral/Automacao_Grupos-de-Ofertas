from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audita arquivo JSON local")
    parser.add_argument(
        "--file",
        required=True,
        help="Caminho do arquivo JSON local",
    )
    parser.add_argument(
        "--save-audit-json",
        default=None,
        help="Caminho opcional para salvar o relatório de auditoria",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    file_path = Path(args.file)

    try:
        content = file_path.read_bytes()
        items = _load_items(content=content)
    except (OSError, ValueError) as error:
        return _print_audit_error(error=error)

    report = _build_report(path=file_path, content=content, items=items)

    if args.save_audit_json:
        try:
            output_path = Path(args.save_audit_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(report, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            return _print_audit_error(error=error)
        print(f"INFO | Auditoria local salva em {output_path}")

    print(f"INFO | Arquivo: {report['path']}")
    print(f"INFO | Tamanho: {report['size_bytes']} bytes")
    print(f"INFO | SHA-256: {report['sha256']}")
    print(f"INFO | Total: {report['total']}")
    for status, count in sorted(report["status_counts"].items()):
        print(f"INFO | {status}: {count}")
    print(f"INFO | Válido: {report['valid']}")
    print("INFO | Nenhum envio foi executado.")
    return 0 if report["valid"] else 3


def _load_items(content: bytes) -> list[dict[str, Any]]:
    try:
        payload = json.loads(content.decode("utf-8"))
    except UnicodeDecodeError as error:
        msg = "Arquivo local não está em UTF-8"
        raise ValueError(msg) from error
    except json.JSONDecodeError as error:
        msg = "Arquivo local não contém JSON válido"
        raise ValueError(msg) from error

    if not isinstance(payload, list):
        msg = "Arquivo local deve conter uma lista"
        raise ValueError(msg)

    items: list[dict[str, Any]] = []
    for raw_item in payload:
        if not isinstance(raw_item, dict):
            msg = "Cada item deve ser um objeto"
            raise ValueError(msg)
        items.append(raw_item)
    return items


def _build_report(
    path: Path,
    content: bytes,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts = Counter(str(item.get("status", "unknown")) for item in items)
    issues = _find_issues(items)
    return {
        "path": str(path),
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "total": len(items),
        "status_counts": dict(sorted(status_counts.items())),
        "valid": not issues,
        "issues": issues,
    }


def _find_issues(items: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    if not items:
        issues.append("arquivo sem itens")

    for index, item in enumerate(items, start=1):
        if not str(item.get("status", "")).strip():
            issues.append(f"item {index} sem status")
        if not str(item.get("target", "")).strip():
            issues.append(f"item {index} sem target")
        if not str(item.get("created_at", "")).strip():
            issues.append(f"item {index} sem created_at")
    return issues


def _print_audit_error(error: Exception) -> int:
    print("ERRO | Não foi possível auditar o arquivo local", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho e formato do arquivo.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

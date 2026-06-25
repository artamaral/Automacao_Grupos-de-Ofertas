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
    parser = argparse.ArgumentParser(
        description="Consolida revisao local em um relatorio JSON"
    )
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
        "--dispatch-artifact-json",
        required=True,
        help="Caminho do artefato local de disparo",
    )
    parser.add_argument(
        "--dispatch-report-json",
        required=True,
        help="Caminho do relatorio local de disparo",
    )
    parser.add_argument(
        "--save-bundle-json",
        required=True,
        help="Caminho local para salvar o relatorio consolidado",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        queue_file = _load_json_list_file(Path(args.queue_json))
        approved_file = _load_json_list_file(Path(args.approved_messages_json))
        manifest_file = _load_json_list_file(Path(args.manifest_json))
        dispatch_artifact_file = _load_json_object_file(Path(args.dispatch_artifact_json))
        dispatch_report_file = _load_json_object_file(Path(args.dispatch_report_json))
        report = _build_bundle_report(
            queue_file=queue_file,
            approved_file=approved_file,
            manifest_file=manifest_file,
            dispatch_artifact_file=dispatch_artifact_file,
            dispatch_report_file=dispatch_report_file,
        )
        output_path = Path(args.save_bundle_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
    except (OSError, ValueError) as error:
        return _print_bundle_error(error=error)

    print(f"INFO | Relatorio consolidado salvo em {output_path}")
    print(f"INFO | Fila pendente: {report['checks']['queue_pending']}")
    print(f"INFO | Mensagens aprovadas: {report['checks']['approved_messages']}")
    print(f"INFO | Itens prontos no manifesto: {report['checks']['manifest_ready']}")
    print(f"INFO | Destinos no dispatch: {report['checks']['dispatch_targets']}")
    print(
        f"INFO | Mensagens no dispatch report: "
        f"{report['checks']['dispatch_report_messages']}"
    )
    print(f"INFO | Valido: {report['valid']}")
    print("INFO | Nenhum envio foi executado.")
    return 0 if report["valid"] else 3


def _load_json_list_file(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    payload = _decode_json_bytes(path=path, content=content)
    if not isinstance(payload, list):
        msg = f"{path} deve conter uma lista"
        raise ValueError(msg)

    for raw_item in payload:
        if not isinstance(raw_item, dict):
            msg = f"{path} contem item que nao e objeto"
            raise ValueError(msg)

    return {
        "path": str(path),
        "content": content,
        "items": payload,
    }


def _load_json_object_file(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    payload = _decode_json_bytes(path=path, content=content)
    if not isinstance(payload, dict):
        msg = f"{path} deve conter um objeto"
        raise ValueError(msg)

    return {
        "path": str(path),
        "content": content,
        "payload": payload,
    }


def _decode_json_bytes(*, path: Path, content: bytes) -> object:
    try:
        return json.loads(content.decode("utf-8"))
    except UnicodeDecodeError as error:
        msg = f"{path} nao esta em UTF-8"
        raise ValueError(msg) from error
    except json.JSONDecodeError as error:
        msg = f"{path} nao contem JSON valido"
        raise ValueError(msg) from error


def _build_bundle_report(
    *,
    queue_file: dict[str, Any],
    approved_file: dict[str, Any],
    manifest_file: dict[str, Any],
    dispatch_artifact_file: dict[str, Any],
    dispatch_report_file: dict[str, Any],
) -> dict[str, Any]:
    queue_items = _list_items(queue_file)
    approved_items = _list_items(approved_file)
    manifest_items = _list_items(manifest_file)
    dispatch_artifact = _object_payload(dispatch_artifact_file)
    dispatch_report = _object_payload(dispatch_report_file)
    queue_status_counts = _status_counts(queue_items)
    manifest_status_counts = _status_counts(manifest_items)
    issues = _find_issues(
        queue_status_counts=queue_status_counts,
        approved_items=approved_items,
        manifest_items=manifest_items,
        manifest_status_counts=manifest_status_counts,
        dispatch_artifact=dispatch_artifact,
        dispatch_report=dispatch_report,
    )
    return {
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "files": {
            "queue": _list_file_report(queue_file, queue_status_counts),
            "approved_messages": _list_file_report(
                approved_file,
                _status_counts(approved_items),
            ),
            "manifest": _list_file_report(manifest_file, manifest_status_counts),
            "dispatch_artifact": _object_file_report(dispatch_artifact_file),
            "dispatch_report": _object_file_report(dispatch_report_file),
        },
        "checks": {
            "queue_pending": queue_status_counts.get("pending", 0),
            "approved_messages": len(approved_items),
            "manifest_items": len(manifest_items),
            "manifest_ready": manifest_status_counts.get("ready", 0),
            "dispatch_targets": len(_target_index(dispatch_artifact)),
            "dispatch_available_messages": _summary_int(
                dispatch_artifact, "total_available_messages"
            ),
            "dispatch_selected_messages": _summary_int(
                dispatch_artifact, "total_selected_messages"
            ),
            "dispatch_report_messages": _summary_int(dispatch_report, "total_messages"),
            "dispatch_report_selected_messages": _summary_int(
                dispatch_report, "total_selected_messages"
            ),
        },
        "valid": not issues,
        "issues": issues,
    }


def _list_items(file_data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(file_data["items"])


def _object_payload(file_data: dict[str, Any]) -> dict[str, Any]:
    return dict(file_data["payload"])


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(item.get("status", "unknown")) for item in items)
    return dict(sorted(counts.items()))


def _list_file_report(file_data: dict[str, Any], status_counts: dict[str, int]) -> dict[str, Any]:
    content = bytes(file_data["content"])
    return {
        "path": file_data["path"],
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "items": len(_list_items(file_data)),
        "status_counts": status_counts,
    }


def _object_file_report(file_data: dict[str, Any]) -> dict[str, Any]:
    content = bytes(file_data["content"])
    payload = _object_payload(file_data)
    return {
        "path": file_data["path"],
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "keys": sorted(str(item) for item in payload.keys()),
    }


def _find_issues(
    *,
    queue_status_counts: dict[str, int],
    approved_items: list[dict[str, Any]],
    manifest_items: list[dict[str, Any]],
    manifest_status_counts: dict[str, int],
    dispatch_artifact: dict[str, Any],
    dispatch_report: dict[str, Any],
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
    issues.extend(
        _find_dispatch_issues(
            manifest_items=manifest_items,
            dispatch_artifact=dispatch_artifact,
            dispatch_report=dispatch_report,
        )
    )
    return issues


def _find_dispatch_issues(
    *,
    manifest_items: list[dict[str, Any]],
    dispatch_artifact: dict[str, Any],
    dispatch_report: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    manifest_count = len(manifest_items)
    artifact_available = _summary_int(dispatch_artifact, "total_available_messages")
    artifact_selected = _summary_int(dispatch_artifact, "total_selected_messages")
    report_total_messages = _summary_int(dispatch_report, "total_messages")
    report_selected = _summary_int(dispatch_report, "total_selected_messages")

    if artifact_available != manifest_count:
        issues.append("dispatch artifact difere do total ready do manifesto")
    if artifact_selected != report_total_messages:
        issues.append("dispatch artifact e dispatch report divergem em mensagens da rodada")
    if report_selected != artifact_selected:
        issues.append("dispatch report diverge do total selecionado no artifact")
    if str(dispatch_report.get("source_generated_at", "")) != str(
        dispatch_artifact.get("generated_at", "")
    ):
        issues.append("dispatch report referencia generated_at diferente do artifact")
    if str(dispatch_report.get("source_timezone", "")) != str(
        dispatch_artifact.get("timezone", "")
    ):
        issues.append("dispatch report referencia timezone diferente do artifact")

    artifact_targets = _target_index(dispatch_artifact)
    report_targets = _target_index(dispatch_report)
    if set(artifact_targets) != set(report_targets):
        issues.append("dispatch artifact e dispatch report divergem em destinos")
    else:
        for key, artifact_target in artifact_targets.items():
            report_target = report_targets[key]
            if int(artifact_target.get("message_count", 0)) != int(
                report_target.get("message_count", 0)
            ):
                issues.append(
                    "dispatch artifact e dispatch report divergem em quantidade por destino"
                )
                break
    return issues


def _summary_int(payload: dict[str, Any], key: str) -> int:
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        return 0
    return int(summary.get(key, 0))


def _target_index(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    raw_targets = payload.get("targets", [])
    if not isinstance(raw_targets, list):
        return {}
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for target in raw_targets:
        if not isinstance(target, dict):
            continue
        key = (
            str(target.get("target", "")),
            str(target.get("adapter_kind", "")),
        )
        index[key] = target
    return index


def _print_bundle_error(error: Exception) -> int:
    print("ERRO | Nao foi possivel consolidar revisao local", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("ACAO | Verifique caminhos e formato dos arquivos locais.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

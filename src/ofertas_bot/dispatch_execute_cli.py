from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ofertas_bot.channel_adapters import (
    BaseDryRunChannelAdapter,
    ChannelAdapterError,
    build_channel_adapter,
)
from ofertas_bot.storage.json_message_draft_store import (
    MessageDraftStoreError,
    message_draft_from_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa dry-run do artefato de disparo e salva relatório local"
    )
    parser.add_argument(
        "--dispatch-artifact-json",
        required=True,
        help="Caminho do artefato local de disparo",
    )
    parser.add_argument(
        "--save-dispatch-report-json",
        required=True,
        help="Caminho local para salvar o relatório de dry-run",
    )
    parser.add_argument(
        "--adapter-kind",
        default=None,
        help="Sobrescreve o adaptador do artefato (console, whatsapp ou telegram)",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        artifact = _load_dispatch_artifact(Path(args.dispatch_artifact_json))
        report = execute_dispatch_artifact(
            artifact,
            adapter_kind_override=args.adapter_kind,
        )
        output_path = Path(args.save_dispatch_report_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, ValueError, MessageDraftStoreError, ChannelAdapterError) as error:
        return _print_dispatch_execute_error(error=error)

    print(f"INFO | Relatório de disparo salvo em {args.save_dispatch_report_json}")
    print(f"INFO | Adaptador: {report['adapter_kind']}")
    print(f"INFO | Destinos processados: {report['summary']['total_targets']}")
    print(f"INFO | Mensagens simuladas: {report['summary']['total_messages']}")
    print("INFO | Nenhum envio real foi executado.")
    return 0


def execute_dispatch_artifact(
    artifact: dict[str, Any],
    *,
    adapter_kind_override: str | None = None,
) -> dict[str, Any]:
    targets = artifact.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("Artefato de disparo vazio ou invalido")

    target_reports: list[dict[str, Any]] = []
    total_messages = 0
    adapter_kinds: set[str] = set()

    for raw_target in targets:
        target_report = _execute_target(
            raw_target=raw_target,
            adapter_kind_override=adapter_kind_override,
        )
        total_messages += target_report["message_count"]
        adapter_kinds.add(str(target_report["adapter_kind"]))
        target_reports.append(target_report)

    return {
        "generated_at": _utc_now_iso(),
        "mode": "dry-run",
        "adapter_kind": adapter_kind_override or _summarize_adapter_kinds(adapter_kinds),
        "summary": {
            "total_targets": len(target_reports),
            "total_messages": total_messages,
            "total_sent": sum(target["sent_messages"] for target in target_reports),
            "total_dry_run": sum(target["dry_run_messages"] for target in target_reports),
        },
        "targets": target_reports,
    }


def _execute_target(
    *,
    raw_target: object,
    adapter_kind_override: str | None = None,
) -> dict[str, Any]:
    if not isinstance(raw_target, dict):
        raise ValueError("Destino do artefato deve ser um objeto")

    target = str(raw_target.get("target", "")).strip()
    if not target:
        raise ValueError("Destino do artefato sem target")
    adapter_kind = str(raw_target.get("adapter_kind", "")).strip().lower()
    if adapter_kind_override is not None:
        adapter_kind = adapter_kind_override.strip().lower()
    adapter = build_channel_adapter(adapter_kind)

    raw_messages = raw_target.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ValueError(f"Destino sem mensagens: {target}")

    message_reports: list[dict[str, Any]] = []
    for raw_message in raw_messages:
        message_reports.append(
            _execute_message(
                adapter=adapter,
                target=target,
                raw_message=raw_message,
            )
        )

    return {
        "target": target,
        "status": "simulated",
        "adapter_kind": adapter.kind,
        "max_messages_per_run": int(raw_target.get("max_messages_per_run", 0)),
        "min_interval_seconds": int(raw_target.get("min_interval_seconds", 0)),
        "message_count": len(message_reports),
        "sent_messages": sum(1 for item in message_reports if item["sent"]),
        "dry_run_messages": sum(1 for item in message_reports if item["dry_run"]),
        "messages": message_reports,
    }


def _execute_message(
    *,
    adapter: BaseDryRunChannelAdapter,
    target: str,
    raw_message: object,
) -> dict[str, Any]:
    if not isinstance(raw_message, dict):
        raise ValueError("Mensagem do artefato deve ser um objeto")

    draft = message_draft_from_json(raw_message.get("draft"))
    result = adapter.publish(draft=draft, target=target)
    return {
        "manifest_item_number": int(raw_message.get("manifest_item_number", 0)),
        "created_at": str(raw_message.get("created_at", "")),
        "planned_offset_seconds": int(raw_message.get("planned_offset_seconds", 0)),
        "status": str(raw_message.get("status", "")),
        "adapter_kind": result.adapter_kind,
        "delivery_label": result.delivery_label,
        "sent": result.sent,
        "dry_run": result.dry_run,
        "target": result.target,
        "text": result.message,
        "offer": {
            "title": draft.offer.title,
            "niche": draft.offer.niche,
            "marketplace": draft.offer.marketplace.value,
            "url": draft.offer.url,
            "price": draft.offer.price,
        },
    }


def _load_dispatch_artifact(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        msg = f"Nao foi possivel ler {path}"
        raise ValueError(msg) from error
    except json.JSONDecodeError as error:
        msg = "Artefato de disparo nao contem JSON valido"
        raise ValueError(msg) from error

    if not isinstance(payload, dict):
        raise ValueError("Artefato de disparo deve ser um objeto")
    return payload


def _summarize_adapter_kinds(adapter_kinds: set[str]) -> str:
    if not adapter_kinds:
        raise ValueError("Artefato de disparo sem adaptadores")
    if len(adapter_kinds) == 1:
        return next(iter(adapter_kinds))
    return "mixed"


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _print_dispatch_execute_error(error: Exception) -> int:
    print("ERRO | Nao foi possivel executar o dry-run do disparo", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("ACAO | Verifique caminho e formato do artefato de disparo.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

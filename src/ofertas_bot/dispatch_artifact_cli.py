from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ofertas_bot.storage.json_message_draft_store import message_draft_to_json
from ofertas_bot.storage.json_publication_manifest_store import (
    JsonPublicationManifestStore,
    PublicationManifestItem,
    PublicationManifestStoreError,
)

try:
    SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    SAO_PAULO_TZ = timezone(timedelta(hours=-3), name="America/Sao_Paulo")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera artefato local de disparo a partir do manifesto"
    )
    parser.add_argument(
        "--manifest-json",
        required=True,
        help="Caminho do arquivo local de manifesto",
    )
    parser.add_argument(
        "--save-dispatch-artifact-json",
        required=True,
        help="Caminho local para salvar o artefato de disparo",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        manifest = JsonPublicationManifestStore(path=Path(args.manifest_json)).load()
        artifact = build_dispatch_artifact(manifest)
        output_path = Path(args.save_dispatch_artifact_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, PublicationManifestStoreError, ValueError) as error:
        return _print_dispatch_error(error=error)

    print(f"INFO | Artefato de disparo salvo em {args.save_dispatch_artifact_json}")
    print(f"INFO | Total de destinos: {artifact['summary']['total_targets']}")
    print(f"INFO | Total de mensagens: {artifact['summary']['total_messages']}")
    print("INFO | Nenhum envio foi executado.")
    return 0


def build_dispatch_artifact(
    manifest: tuple[PublicationManifestItem, ...],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not manifest:
        raise ValueError("Manifesto local vazio")
    current_time = _project_now(now)

    grouped_items: dict[tuple[str, str], list[tuple[int, PublicationManifestItem]]] = {}
    for item_number, item in enumerate(manifest, start=1):
        if item.status != "ready":
            raise ValueError("Manifesto possui item fora do status ready")
        grouped_items.setdefault(
            (item.target, item.channel_adapter), []
        ).append((item_number, item))

    targets = [
        _build_target_entry(
            target=target,
            adapter_kind=adapter_kind,
            indexed_items=items,
            now=current_time,
        )
        for (target, adapter_kind), items in sorted(grouped_items.items())
    ]

    return {
        "generated_at": current_time.isoformat(),
        "timezone": "America/Sao_Paulo",
        "summary": {
            "total_targets": len(targets),
            "total_available_messages": sum(
                target["available_message_count"] for target in targets
            ),
            "total_selected_messages": sum(target["message_count"] for target in targets),
            "total_skipped_messages": sum(
                target["skipped_message_count"] for target in targets
            ),
            "total_blocked_targets": sum(
                1 for target in targets if target["status"] == "blocked"
            ),
            "total_messages": sum(target["message_count"] for target in targets),
        },
        "targets": targets,
    }


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _build_target_entry(
    *,
    target: str,
    adapter_kind: str,
    indexed_items: list[tuple[int, PublicationManifestItem]],
    now: datetime,
) -> dict[str, Any]:
    if not indexed_items:
        raise ValueError("Destino sem itens no manifesto")
    reference_item = indexed_items[0][1]
    max_messages_per_run = reference_item.max_messages_per_run
    max_messages_per_hour = reference_item.max_messages_per_hour
    min_interval_seconds = reference_item.min_interval_seconds
    quiet_periods = reference_item.quiet_periods
    effective_limit = _effective_message_limit(
        max_messages_per_run=max_messages_per_run,
        max_messages_per_hour=max_messages_per_hour,
    )
    quiet_period_active = _is_quiet_period_active(now=now, quiet_periods=quiet_periods)
    selected_items = []
    if not quiet_period_active:
        selected_items = (
            indexed_items[:effective_limit]
            if effective_limit > 0
            else list(indexed_items)
        )
    skipped_message_count = len(indexed_items) - len(selected_items)

    messages = [
        _build_message_entry(
            manifest_item_number=manifest_item_number,
            item=item,
            offset_index=offset_index,
            min_interval_seconds=min_interval_seconds,
            base_time=now,
        )
        for offset_index, (manifest_item_number, item) in enumerate(selected_items, start=1)
    ]

    return {
        "target": target,
        "adapter_kind": adapter_kind,
        "status": "blocked" if quiet_period_active else "ready",
        "available_message_count": len(indexed_items),
        "message_count": len(messages),
        "selected_message_count": len(messages),
        "skipped_message_count": skipped_message_count,
        "max_messages_per_run": max_messages_per_run,
        "max_messages_per_hour": max_messages_per_hour,
        "min_interval_seconds": min_interval_seconds,
        "quiet_periods": list(quiet_periods),
        "quiet_period_active": quiet_period_active,
        "blocked_reason": _build_blocked_reason(
            quiet_period_active=quiet_period_active,
        ),
        "selection_reason": _build_selection_reason(
            quiet_period_active=quiet_period_active,
            available_message_count=len(indexed_items),
            selected_message_count=len(messages),
            max_messages_per_run=max_messages_per_run,
            max_messages_per_hour=max_messages_per_hour,
        ),
        "first_planned_at": messages[0]["planned_at"] if messages else None,
        "last_planned_at": messages[-1]["planned_at"] if messages else None,
        "messages": messages,
    }


def _effective_message_limit(
    *,
    max_messages_per_run: int,
    max_messages_per_hour: int,
) -> int:
    positive_limits = [
        value for value in (max_messages_per_run, max_messages_per_hour) if value > 0
    ]
    if not positive_limits:
        return 0
    return min(positive_limits)


def _is_quiet_period_active(*, now: datetime, quiet_periods: tuple[str, ...]) -> bool:
    if not quiet_periods:
        return False
    current_time = now.timetz().replace(tzinfo=None)
    for quiet_period in quiet_periods:
        start, end = _parse_quiet_period(quiet_period)
        if start < end and start <= current_time < end:
            return True
        if start > end and (current_time >= start or current_time < end):
            return True
    return False


def _parse_quiet_period(value: str) -> tuple[time, time]:
    start_value, end_value = value.split("-", maxsplit=1)
    return time.fromisoformat(start_value), time.fromisoformat(end_value)


def _build_blocked_reason(*, quiet_period_active: bool) -> str | None:
    if quiet_period_active:
        return "quiet_period_active"
    return None


def _build_selection_reason(
    *,
    quiet_period_active: bool,
    available_message_count: int,
    selected_message_count: int,
    max_messages_per_run: int,
    max_messages_per_hour: int,
) -> str | None:
    if quiet_period_active:
        return "quiet_period_active"
    if selected_message_count >= available_message_count:
        return None
    positive_limits = {
        "max_messages_per_run": max_messages_per_run,
        "max_messages_per_hour": max_messages_per_hour,
    }
    active_limits = [
        label
        for label, value in positive_limits.items()
        if value > 0 and value == selected_message_count
    ]
    if not active_limits:
        return "selection_limited"
    return ",".join(sorted(active_limits))


def _build_message_entry(
    *,
    manifest_item_number: int,
    item: PublicationManifestItem,
    offset_index: int,
    min_interval_seconds: int,
    base_time: datetime,
) -> dict[str, Any]:
    planned_offset_seconds = (offset_index - 1) * min_interval_seconds
    planned_at = base_time + timedelta(seconds=planned_offset_seconds)
    return {
        "manifest_item_number": manifest_item_number,
        "status": item.status,
        "created_at": item.created_at,
        "planned_offset_seconds": planned_offset_seconds,
        "planned_at": planned_at.isoformat(),
        "text": item.draft.text,
        "draft": message_draft_to_json(item.draft),
        "offer": {
            "marketplace": item.draft.offer.marketplace.value,
            "niche": item.draft.offer.niche,
            "title": item.draft.offer.title,
            "url": item.draft.offer.url,
            "price": item.draft.offer.price,
            "old_price": item.draft.offer.old_price,
        },
    }


def _project_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(SAO_PAULO_TZ).replace(microsecond=0)
    reference = now if now.tzinfo is not None else now.replace(tzinfo=SAO_PAULO_TZ)
    return reference.astimezone(SAO_PAULO_TZ).replace(microsecond=0)


def _print_dispatch_error(error: Exception) -> int:
    print("ERRO | Não foi possível gerar o artefato de disparo", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminho e formato do manifesto local.", file=sys.stderr)
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

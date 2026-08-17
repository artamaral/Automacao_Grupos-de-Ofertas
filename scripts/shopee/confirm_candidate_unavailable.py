from __future__ import annotations

import argparse
import csv
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from ofertas_bot.candidate_refresh import CandidateRefreshError
from ofertas_bot.storage.supabase_candidate_refresh_store import (
    SupabaseCandidateRefreshStore,
)

CONFIRMATION = "CONFIRM_CANDIDATE_UNAVAILABLE"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Marca candidatos Shopee como indisponiveis confirmados para sair da fila automatica."
    )
    parser.add_argument("--profile", required=True)
    parser.add_argument("--marketplace", default="shopee")
    parser.add_argument("--item-id", type=int, action="append", default=None)
    parser.add_argument("--refresh-attempts-file", type=Path, default=None)
    parser.add_argument(
        "--reason",
        default="manual review confirmed item unavailable after no_node refresh response",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _validate_args(args)
        item_ids = _resolve_item_ids(
            explicit_item_ids=args.item_id or (),
            refresh_attempts_file=args.refresh_attempts_file,
        )
        if not item_ids:
            raise CandidateRefreshError("nenhum item elegivel para confirmacao manual")

        store = SupabaseCandidateRefreshStore.connect_from_env()
        try:
            confirmed_at = datetime.now(UTC)
            for item_id in item_ids:
                store.record_unavailable_confirmation(
                    profile=args.profile,
                    marketplace=args.marketplace,
                    item_id=item_id,
                    confirmed_at=confirmed_at,
                    reason=args.reason,
                )
        finally:
            store.close()
    except Exception as error:  # noqa: BLE001
        print("ERRO | Confirmacao manual bloqueada", file=sys.stderr)
        print(f"DETALHE | {error}", file=sys.stderr)
        return 3

    print(f"INFO | Confirmacao manual concluida para {len(item_ids)} item(ns)")
    print("INFO | Itens confirmados: " + ",".join(str(item_id) for item_id in item_ids))
    return 0


def _validate_args(args: argparse.Namespace) -> None:
    if args.profile != "feminino":
        raise CandidateRefreshError("this version only supports --profile feminino")
    if args.marketplace != "shopee":
        raise CandidateRefreshError("this version only supports --marketplace shopee")
    if not args.apply:
        raise CandidateRefreshError("--apply is required")
    if args.confirm_remote_write != CONFIRMATION:
        raise CandidateRefreshError(
            f"--confirm-remote-write must be exactly {CONFIRMATION}"
        )


def _resolve_item_ids(
    *,
    explicit_item_ids: Sequence[int],
    refresh_attempts_file: Path | None,
) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for item_id in explicit_item_ids:
        if item_id <= 0:
            raise CandidateRefreshError("--item-id must be positive")
        if item_id not in seen:
            seen.add(item_id)
            ordered.append(item_id)

    if refresh_attempts_file is not None:
        if not refresh_attempts_file.is_file():
            raise CandidateRefreshError(
                f"refresh attempts file not found: {refresh_attempts_file}"
            )
        with refresh_attempts_file.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("status") != "no_node":
                    continue
                raw_item_id = str(row.get("item_id", "")).strip()
                if not raw_item_id:
                    continue
                item_id = int(raw_item_id)
                if item_id not in seen:
                    seen.add(item_id)
                    ordered.append(item_id)

    return ordered


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from ofertas_bot.candidate_refresh import AUTO_CONFIRMATION_SOURCE, CandidateRefreshError
from ofertas_bot.storage.supabase_candidate_refresh_store import (
    SupabaseCandidateRefreshStore,
)

CONFIRMATION = "AUTO_CONFIRM_CANDIDATE_UNAVAILABLE"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Marca automaticamente candidatos Shopee como indisponiveis confirmados "
            "apos repeticoes de no_node."
        )
    )
    parser.add_argument("--profile", required=True)
    parser.add_argument("--marketplace", default="shopee")
    parser.add_argument("--refresh-attempts-file", type=Path, required=True)
    parser.add_argument("--min-no-node-attempts", type=int, default=2)
    parser.add_argument(
        "--reason",
        default="automatic confirmation after repeated no_node refresh responses",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _validate_args(args)
        current_run_item_ids = _resolve_current_run_no_node_item_ids(args.refresh_attempts_file)
        if not current_run_item_ids:
            print("INFO | Nenhum no_node na rodada atual")
            return 0

        store = SupabaseCandidateRefreshStore.connect_from_env()
        try:
            eligible_item_ids = store.load_auto_confirmable_unavailable_item_ids(
                profile=args.profile,
                marketplace=args.marketplace,
                item_ids=current_run_item_ids,
                min_no_node_attempts=args.min_no_node_attempts,
            )
            if not eligible_item_ids:
                print(
                    "INFO | Nenhum item atingiu o limite para confirmacao automatica"
                )
                print(
                    "INFO | Itens no_node da rodada atual: "
                    + ",".join(str(item_id) for item_id in current_run_item_ids)
                )
                return 0

            confirmed_at = datetime.now(UTC)
            for item_id in eligible_item_ids:
                store.record_unavailable_confirmation(
                    profile=args.profile,
                    marketplace=args.marketplace,
                    item_id=item_id,
                    confirmed_at=confirmed_at,
                    reason=args.reason,
                    source=AUTO_CONFIRMATION_SOURCE,
                    error_type="AutoConfirmation",
                )
        finally:
            store.close()
    except Exception as error:  # noqa: BLE001
        print("ERRO | Confirmacao automatica bloqueada", file=sys.stderr)
        print(f"DETALHE | {error}", file=sys.stderr)
        return 3

    print(
        "INFO | Confirmacao automatica concluida para "
        f"{len(eligible_item_ids)} item(ns)"
    )
    print(
        "INFO | Itens confirmados automaticamente: "
        + ",".join(str(item_id) for item_id in eligible_item_ids)
    )
    return 0


def _validate_args(args: argparse.Namespace) -> None:
    if args.profile != "feminino":
        raise CandidateRefreshError("this version only supports --profile feminino")
    if args.marketplace != "shopee":
        raise CandidateRefreshError("this version only supports --marketplace shopee")
    if args.min_no_node_attempts <= 0:
        raise CandidateRefreshError("--min-no-node-attempts must be positive")
    if not args.apply:
        raise CandidateRefreshError("--apply is required")
    if args.confirm_remote_write != CONFIRMATION:
        raise CandidateRefreshError(
            f"--confirm-remote-write must be exactly {CONFIRMATION}"
        )


def _resolve_current_run_no_node_item_ids(refresh_attempts_file: Path) -> list[int]:
    if not refresh_attempts_file.is_file():
        raise CandidateRefreshError(
            f"refresh attempts file not found: {refresh_attempts_file}"
        )

    seen: set[int] = set()
    ordered: list[int] = []
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

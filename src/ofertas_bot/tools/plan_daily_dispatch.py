from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ofertas_bot.daily_dispatch_planner import (
    load_daily_planning_policy,
    plan_daily_dispatches,
    plan_productcatid_dispatches,
)
from ofertas_bot.productcatid_catalog import load_product_category_quotas
from ofertas_bot.storage.supabase_dispatch_plan_store import SupabaseDispatchPlanStore


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and persist the daily dispatch plan.")
    parser.add_argument("--profile", default="feminino")
    parser.add_argument("--marketplace", default="shopee")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=datetime.now(ZoneInfo("America/Sao_Paulo")).date(),
    )
    parser.add_argument("--policy", type=Path, default=Path("config/selection_profiles.toml"))
    parser.add_argument(
        "--productcatid-matrix",
        type=Path,
        help="Use exact productCatId quotas. This mode is enabled only at cutover.",
    )
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    policy = load_daily_planning_policy(
        args.policy,
        profile=args.profile,
        marketplace=args.marketplace,
    )
    store = SupabaseDispatchPlanStore.connect_from_env()
    try:
        candidates = store.load_candidates(
            profile=args.profile,
            marketplace=args.marketplace,
            planned_date=args.date,
            productcatid_only=bool(args.productcatid_matrix),
        )
        if args.productcatid_matrix:
            quotas = load_product_category_quotas(args.productcatid_matrix)
            plan = plan_productcatid_dispatches(
                candidates,
                quotas=quotas,
                policy=policy,
                planned_date=args.date,
            )
        else:
            plan = plan_daily_dispatches(candidates, policy=policy, planned_date=args.date)
        if args.apply:
            store.replace_day(
                profile=args.profile,
                marketplace=args.marketplace,
                planned_date=args.date,
                items=plan,
            )
    finally:
        store.close()
    print(
        f"profile={args.profile} date={args.date.isoformat()} candidates={len(candidates)} "
        f"planned={len(plan)} applied={str(args.apply).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

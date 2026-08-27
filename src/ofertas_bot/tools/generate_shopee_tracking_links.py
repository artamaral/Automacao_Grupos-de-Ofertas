from __future__ import annotations

import argparse
from datetime import date, datetime
from zoneinfo import ZoneInfo

from ofertas_bot.providers.shopee_tracking import ShopeeTrackingProvider
from ofertas_bot.settings import Settings
from ofertas_bot.shopee_tracking_service import generate_tracking_links
from ofertas_bot.storage.supabase_shopee_tracking_store import SupabaseShopeeTrackingStore

CONFIRMATION = "GENERATE_SHOPEE_TRACKING_LINKS"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="feminino")
    parser.add_argument("--date", type=date.fromisoformat,
                        default=datetime.now(ZoneInfo("America/Sao_Paulo")).date())
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    args = parser.parse_args(argv)
    if args.apply and args.confirm_remote_write != CONFIRMATION:
        raise ValueError(f"--confirm-remote-write must be {CONFIRMATION}")
    store = SupabaseShopeeTrackingStore.connect_from_env()
    try:
        provider = ShopeeTrackingProvider.from_settings(Settings()) if args.apply else None
        result = generate_tracking_links(store, provider, args.profile, args.date, apply=args.apply)
    finally:
        store.close()
    print(
        f"selected={result.selected} ready={result.ready} "
        f"failed={result.failed} apply={args.apply}"
    )
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

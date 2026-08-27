from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from ofertas_bot.providers.shopee_tracking import ShopeeTrackingProvider
from ofertas_bot.settings import Settings
from ofertas_bot.shopee_conversion_sync import collect_conversion_report
from ofertas_bot.storage.supabase_shopee_conversion_store import SupabaseShopeeConversionStore
from ofertas_bot.storage.supabase_shopee_tracking_store import SupabaseShopeeTrackingStore

CONFIRMATION = "SYNC_SHOPEE_CONVERSION_REPORT"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    args = parser.parse_args(argv)
    if args.apply and args.confirm_remote_write != CONFIRMATION:
        raise ValueError(f"--confirm-remote-write must be {CONFIRMATION}")
    if not args.apply:
        print("apply=false; no API request or database write performed")
        return 0
    provider = ShopeeTrackingProvider.from_settings(Settings())
    report = collect_conversion_report(provider, datetime.now(ZoneInfo("America/Sao_Paulo")))
    tracking = SupabaseShopeeTrackingStore.connect_from_env()
    store = SupabaseShopeeConversionStore(tracking.connection)
    run_id = store.start_run(report)
    try:
        store.persist(run_id, report)
    except Exception as exc:
        store.fail(run_id, str(exc))
        raise
    finally:
        tracking.close()
    print(
        f"sync_run_id={run_id} purchase_date={report.window.purchase_date} "
        f"nodes={len(report.nodes)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

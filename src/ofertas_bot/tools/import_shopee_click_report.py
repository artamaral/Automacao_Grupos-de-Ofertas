from __future__ import annotations

import argparse
from pathlib import Path

from ofertas_bot.shopee_click_report_importer import parse_click_report
from ofertas_bot.storage.supabase_shopee_click_report_store import SupabaseShopeeClickReportStore
from ofertas_bot.storage.supabase_shopee_tracking_store import SupabaseShopeeTrackingStore

CONFIRMATION = "IMPORT_SHOPEE_CLICK_REPORT"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    args = parser.parse_args(argv)
    if args.apply and args.confirm_remote_write != CONFIRMATION:
        raise ValueError(f"--confirm-remote-write must be {CONFIRMATION}")
    tracking = SupabaseShopeeTrackingStore.connect_from_env()
    try:
        report = parse_click_report(args.file, tracking.lookup_plan)
        imported = 0
        import_id = "dry-run"
        if args.apply:
            import_id, imported = SupabaseShopeeClickReportStore(
                tracking.connection
            ).import_report(report)
    finally:
        tracking.close()
    print(f"import_id={import_id} rows={len(report.events)} imported={imported} apply={args.apply}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

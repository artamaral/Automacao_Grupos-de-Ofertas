from __future__ import annotations

from ofertas_bot.shopee_click_report_importer import PreparedClickReport, event_raw_json


class SupabaseShopeeClickReportStore:
    def __init__(self, connection) -> None:
        self.connection = connection

    def import_report(self, report: PreparedClickReport) -> tuple[str, int]:
        existing = self.connection.execute(
            "select import_id from offers.shopee_click_report_imports where source_sha256=%s",
            (report.sha256,),
        ).fetchone()
        if existing:
            return str(existing["import_id"]), 0
        with self.connection.transaction():
            imported = self.connection.execute(
                """insert into offers.shopee_click_report_imports
                (source_filename, source_sha256, row_count, status)
                values (%s,%s,%s,'imported') returning import_id""",
                (report.filename, report.sha256, len(report.events)),
            ).fetchone()
            import_id = imported["import_id"]
            for event in report.events:
                self.connection.execute(
                    """insert into offers.shopee_click_events
                    (import_id,click_id,click_time,click_region,referrer,sub_id_raw,
                    tracking_channel,tracking_profile,tracking_dispatch_id,tracking_item_id,
                    dispatch_plan_id,tracking_parse_status,raw_row)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                    (import_id, event.click_id, event.click_time, event.click_region,
                     event.referrer,
                     event.sub_id_raw, event.tracking_channel, event.tracking_profile,
                     event.tracking_dispatch_id, event.tracking_item_id, event.dispatch_plan_id,
                     event.tracking_parse_status, event_raw_json(event)),
                )
        return str(import_id), len(report.events)

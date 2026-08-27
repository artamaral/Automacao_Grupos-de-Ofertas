from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from ofertas_bot.shopee_conversion_sync import CollectedConversionReport, query_filters
from ofertas_bot.shopee_tracking import api_time, conversion_node_key, resolve_dispatch_token


class SupabaseShopeeConversionStore:
    def __init__(self, connection) -> None:
        self.connection = connection

    def start_run(self, report: CollectedConversionReport) -> str:
        row = self.connection.execute(
            """insert into offers.shopee_conversion_sync_runs(query_filters,status)
            values (%s::jsonb,'running') returning sync_run_id""",
            (json.dumps(query_filters(report.window)),),
        ).fetchone()
        return str(row["sync_run_id"])

    def persist(self, run_id: str, report: CollectedConversionReport) -> None:
        with self.connection.transaction():
            for node in report.nodes:
                self._upsert_node(run_id, node)
            self.connection.execute(
                """update offers.shopee_conversion_sync_runs set status='succeeded',
                finished_at=now(), nodes_received=%s, last_page=%s, page_limit=%s,
                has_next_page=false, last_scroll_id=%s where sync_run_id=%s""",
                (len(report.nodes), report.last_page, report.page_limit,
                 report.last_scroll_id, run_id),
            )

    def fail(self, run_id: str, error: str) -> None:
        self.connection.execute(
            """update offers.shopee_conversion_sync_runs set status='failed',
            finished_at=now(), error=%s where sync_run_id=%s""", (error[:4000], run_id)
        )

    def _upsert_node(self, run_id: str, node: dict[str, Any]) -> None:
        conversion_id = str(node["conversionId"])
        dispatch_id = resolve_dispatch_token(_text(node.get("utmContent")))
        if dispatch_id is not None:
            found = self.connection.execute(
                "select 1 from offers.daily_dispatch_plan where dispatch_plan_id=%s", (dispatch_id,)
            ).fetchone()
            if not found:
                dispatch_id = None
        row = self.connection.execute(
            """insert into offers.shopee_conversions
            (source_node_key,conversion_id,dispatch_plan_id,utm_content_raw,click_time,
             purchase_time,buyer_type,total_commission,net_commission,seller_commission,
             shopee_commission_capped,raw_payload,last_sync_run_id)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
            on conflict (source_node_key) do update set
              conversion_id=excluded.conversion_id, dispatch_plan_id=excluded.dispatch_plan_id,
              utm_content_raw=excluded.utm_content_raw, click_time=excluded.click_time,
              purchase_time=excluded.purchase_time, buyer_type=excluded.buyer_type,
              total_commission=excluded.total_commission, net_commission=excluded.net_commission,
              seller_commission=excluded.seller_commission,
              shopee_commission_capped=excluded.shopee_commission_capped,
              raw_payload=excluded.raw_payload,last_sync_run_id=excluded.last_sync_run_id,
              last_seen_at=now(),updated_at=now()
            returning conversion_record_id""",
            (conversion_node_key(node), conversion_id, dispatch_id, _text(node.get("utmContent")),
             api_time(node.get("clickTime")), api_time(node.get("purchaseTime")),
             _text(node.get("buyerType")), _number(node.get("totalCommission")),
             _number(node.get("netCommission")), _number(node.get("sellerCommission")),
             _number(node.get("shopeeCommissionCapped")), json.dumps(node), run_id),
        ).fetchone()
        record_id = row["conversion_record_id"]
        self.connection.execute(
            "delete from offers.shopee_conversion_orders where conversion_record_id=%s",
            (record_id,),
        )
        for order in node.get("orders") or []:
            order_id = str(order.get("orderId") or "").strip()
            if not order_id:
                raise ValueError("orderId is required")
            order_row = self.connection.execute(
                """insert into offers.shopee_conversion_orders
                (conversion_record_id,conversion_id,order_id,shop_type,order_status,raw_payload)
                values (%s,%s,%s,%s,%s,%s::jsonb) returning conversion_order_id""",
                (record_id, conversion_id, order_id, _text(order.get("shopType")),
                 _text(order.get("orderStatus")), json.dumps(order)),
            ).fetchone()
            for ordinal, item in enumerate(order.get("items") or []):
                self._insert_item(order_row["conversion_order_id"], record_id,
                                  conversion_id, order_id, ordinal, item)

    def _insert_item(self, order_record_id, conversion_record_id, conversion_id: str,
                     order_id: str, ordinal: int, item: dict[str, Any]) -> None:
        self.connection.execute(
            """insert into offers.shopee_conversion_items
            (conversion_order_id,conversion_record_id,conversion_id,order_id,item_ordinal,
             item_id,item_name,item_price,actual_amount,refund_amount,qty,item_total_commission,
             global_category_lv1_name,global_category_lv2_name,global_category_lv3_name,
             fraud_status,attribution_type,complete_time,raw_payload)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
            (order_record_id, conversion_record_id, conversion_id, order_id, ordinal,
             int(item["itemId"]), _text(item.get("itemName")), _number(item.get("itemPrice")),
             _number(item.get("actualAmount")), _number(item.get("refundAmount")),
             int(item["qty"]) if item.get("qty") not in (None, "") else None,
             _number(item.get("itemTotalCommission")), _text(item.get("globalCategoryLv1Name")),
             _text(item.get("globalCategoryLv2Name")), _text(item.get("globalCategoryLv3Name")),
             _text(item.get("fraudStatus")), _text(item.get("attributionType")),
             api_time(item.get("completeTime")), json.dumps(item)),
        )


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any) -> Decimal | None:
    return None if value in (None, "") else Decimal(str(value))

-- Persist the complete send-time snapshot in the daily queue. Dispatch must
-- not expand the ranking views after the plan has been materialized.

alter table offers.daily_dispatch_plan
  add column if not exists product_name text,
  add column if not exists source_offer_link text,
  add column if not exists image_url text,
  add column if not exists price numeric(14, 2),
  add column if not exists reference_price numeric(14, 2),
  add column if not exists sales_count bigint,
  add column if not exists rating numeric(4, 2),
  add column if not exists score_reasons text[],
  add column if not exists rank_profile bigint,
  add column if not exists rank_subniche bigint,
  add column if not exists refresh_status text,
  add column if not exists last_checked_at timestamptz,
  add column if not exists latest_snapshot_id bigint
    references offers.offer_snapshots (id);

create index if not exists daily_dispatch_plan_direct_claim_window_idx
  on offers.daily_dispatch_plan (
    profile, marketplace, planned_date, planned_hour, slot_sequence
  )
  where dispatch_status = 'planned'
    and tracking_status = 'ready'
    and refresh_status = 'FRESH';

create or replace view offers.v_daily_dispatch_ready
with (security_invoker = true)
as
select
  plan.dispatch_plan_id,
  plan.profile,
  plan.marketplace,
  plan.stable_key,
  plan.item_id,
  plan.product_name,
  plan.source_offer_link as offer_link,
  plan.image_url,
  plan.price,
  plan.reference_price,
  plan.rating,
  plan.sales_count,
  plan.primary_subniche,
  plan.commercial_score,
  plan.score_reasons,
  plan.rank_profile,
  plan.rank_subniche,
  plan.selection_bucket,
  plan.selection_reason,
  plan.planned_date,
  plan.planned_hour,
  plan.slot_sequence,
  plan.daily_sequence,
  (
    plan.dispatch_status = 'planned'
    and plan.refresh_status = 'FRESH'
    and plan.last_checked_at is not null
    and (plan.last_checked_at at time zone 'America/Sao_Paulo')::date
      = plan.planned_date
    and plan.latest_snapshot_id is not null
    and btrim(coalesce(plan.product_name, '')) <> ''
    and btrim(coalesce(plan.source_offer_link, '')) <> ''
    and plan.price > 0
  ) as is_ready_for_dispatch,
  plan.dispatch_status,
  plan.claim_token,
  plan.claimed_at,
  plan.created_at as planned_at,
  plan.refresh_status,
  plan.last_checked_at,
  case
    when plan.last_checked_at is null then null
    else extract(epoch from (now() - plan.last_checked_at)) / 3600
  end as age_hours,
  plan.latest_snapshot_id,
  plan.product_cat_id
from offers.daily_dispatch_plan plan;

create or replace view offers.v_daily_dispatch_ready_tracked
with (security_invoker = true)
as
select
  ready.dispatch_plan_id,
  ready.profile,
  ready.marketplace,
  ready.stable_key,
  ready.item_id,
  ready.product_name,
  plan.tracking_short_url as offer_link,
  ready.image_url,
  ready.price,
  ready.reference_price,
  ready.rating,
  ready.sales_count,
  ready.primary_subniche,
  ready.commercial_score,
  ready.score_reasons,
  ready.rank_profile,
  ready.rank_subniche,
  ready.selection_bucket,
  ready.selection_reason,
  ready.planned_date,
  ready.planned_hour,
  ready.slot_sequence,
  ready.daily_sequence,
  (
    ready.is_ready_for_dispatch
    and plan.tracking_status = 'ready'
    and cardinality(plan.tracking_sub_ids) = 4
    and btrim(coalesce(plan.tracking_short_url, '')) <> ''
  ) as is_ready_for_dispatch,
  ready.dispatch_status,
  ready.claim_token,
  ready.claimed_at,
  ready.planned_at,
  ready.refresh_status,
  ready.last_checked_at,
  ready.age_hours,
  ready.latest_snapshot_id,
  plan.tracking_sub_ids,
  plan.tracking_short_url,
  plan.tracking_generated_at,
  plan.tracking_status,
  plan.tracking_error,
  ready.product_cat_id
from offers.v_daily_dispatch_ready ready
join offers.daily_dispatch_plan plan using (dispatch_plan_id);

comment on column offers.daily_dispatch_plan.source_offer_link is
  'Original offer URL captured by the planner; dispatch uses tracking_short_url.';
comment on column offers.daily_dispatch_plan.latest_snapshot_id is
  'Snapshot selected by the planner and frozen with the daily send payload.';
comment on view offers.v_daily_dispatch_ready is
  'Lightweight projection of the persisted daily queue; it does not recalculate ranking.';
comment on view offers.v_daily_dispatch_ready_tracked is
  'Lightweight tracked projection of the persisted daily queue.';

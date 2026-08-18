create or replace view offers.v_daily_dispatch_ready
with (security_invoker = true)
as
select
  plan.dispatch_plan_id,
  plan.profile,
  plan.marketplace,
  plan.stable_key,
  plan.item_id,
  ranking.product_name,
  ranking.offer_link,
  ranking.image_url,
  ranking.price,
  ranking.reference_price,
  ranking.rating,
  ranking.sales_count,
  plan.primary_subniche,
  plan.commercial_score,
  ranking.score_reasons,
  ranking.rank_profile,
  ranking.rank_subniche,
  plan.selection_bucket,
  plan.selection_reason,
  plan.planned_date,
  plan.planned_hour,
  plan.slot_sequence,
  plan.daily_sequence,
  (
    plan.dispatch_status = 'planned'
    and ranking.is_eligible
    and ranking.refresh_status = 'FRESH'
    and ranking.last_checked_at is not null
    and (ranking.last_checked_at at time zone 'America/Sao_Paulo')::date = plan.planned_date
  ) as is_ready_for_dispatch,
  plan.dispatch_status,
  plan.claim_token,
  plan.claimed_at,
  plan.created_at as planned_at,
  ranking.refresh_status,
  ranking.last_checked_at,
  ranking.age_hours,
  ranking.latest_snapshot_id
from offers.daily_dispatch_plan plan
join offers.v_offer_ranking_current ranking
  on ranking.profile = plan.profile
 and ranking.marketplace = plan.marketplace
 and ranking.stable_key = plan.stable_key;

comment on view offers.v_daily_dispatch_ready is
  'Superficie operacional pronta; somente slots elegiveis com snapshot do planned_date em America/Sao_Paulo podem ser consumidos pelo n8n.';

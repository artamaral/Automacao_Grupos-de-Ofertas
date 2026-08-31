create table if not exists offers.shopee_product_categories (
  category_id bigint primary key check (category_id > 0),
  category text not null,
  sub_category text,
  level_3 text,
  level_4 text,
  level_5 text,
  category_path text not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  loaded_at timestamptz not null default now()
);

create table if not exists offers.profile_product_category_quotas (
  profile text not null,
  marketplace text not null default 'shopee',
  product_cat_id bigint not null references offers.shopee_product_categories(category_id),
  daily_quantity integer not null check (daily_quantity > 0),
  enabled boolean not null default true,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  updated_at timestamptz not null default now(),
  primary key (profile, marketplace, product_cat_id)
);

alter table offers.catalog_items
  add column if not exists product_cat_id bigint references offers.shopee_product_categories(category_id),
  add column if not exists catalog_generation text,
  add column if not exists catalog_status text not null default 'legacy' check (catalog_status in ('current', 'legacy')),
  add column if not exists refresh_required_after timestamptz;

alter table offers.catalog_items
  drop constraint if exists catalog_items_subniches_check;

alter table offers.catalog_items
  add constraint catalog_items_subniches_or_product_cat_id_check
  check (cardinality(subniches) > 0 or product_cat_id is not null);

alter table offers.offer_snapshots
  add column if not exists product_cat_id bigint references offers.shopee_product_categories(category_id);

alter table offers.daily_dispatch_plan
  add column if not exists product_cat_id bigint references offers.shopee_product_categories(category_id);

create index if not exists catalog_items_catalog_status_idx on offers.catalog_items(profile, marketplace, catalog_status);
create index if not exists catalog_items_product_cat_status_idx on offers.catalog_items(profile, marketplace, product_cat_id, catalog_status);
create index if not exists daily_dispatch_plan_product_cat_idx on offers.daily_dispatch_plan(profile, marketplace, planned_date, product_cat_id);

alter table offers.shopee_product_categories enable row level security;
alter table offers.profile_product_category_quotas enable row level security;

do $$ begin
  revoke all on offers.shopee_product_categories, offers.profile_product_category_quotas from public;
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on offers.shopee_product_categories, offers.profile_product_category_quotas from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on offers.shopee_product_categories, offers.profile_product_category_quotas from authenticated;
  end if;
end $$;

create or replace view offers.v_daily_dispatch_ready
with (security_invoker = true)
as
select
  plan.dispatch_plan_id, plan.profile, plan.marketplace, plan.stable_key,
  plan.item_id, ranking.product_name, ranking.offer_link,
  ranking.image_url, ranking.price, ranking.reference_price, ranking.rating,
  ranking.sales_count, plan.primary_subniche, plan.commercial_score,
  ranking.score_reasons, ranking.rank_profile, ranking.rank_subniche,
  plan.selection_bucket, plan.selection_reason, plan.planned_date,
  plan.planned_hour, plan.slot_sequence, plan.daily_sequence,
  (plan.dispatch_status = 'planned' and ranking.is_eligible
    and ranking.refresh_status = 'FRESH' and ranking.last_checked_at is not null
    and (ranking.last_checked_at at time zone 'America/Sao_Paulo')::date = plan.planned_date)
    as is_ready_for_dispatch,
  plan.dispatch_status, plan.claim_token, plan.claimed_at, plan.created_at as planned_at,
  ranking.refresh_status, ranking.last_checked_at, ranking.age_hours, ranking.latest_snapshot_id,
  plan.product_cat_id
from offers.daily_dispatch_plan plan
join offers.v_offer_ranking_current ranking
  on ranking.profile = plan.profile and ranking.marketplace = plan.marketplace
 and ranking.stable_key = plan.stable_key;

create or replace view offers.v_daily_dispatch_ready_tracked
with (security_invoker = true)
as
select
  ready.dispatch_plan_id, ready.profile, ready.marketplace, ready.stable_key,
  ready.item_id, ready.product_name,
  plan.tracking_short_url as offer_link, ready.image_url, ready.price,
  ready.reference_price, ready.rating, ready.sales_count, ready.primary_subniche,
  ready.commercial_score, ready.score_reasons, ready.rank_profile, ready.rank_subniche,
  ready.selection_bucket, ready.selection_reason, ready.planned_date, ready.planned_hour,
  ready.slot_sequence, ready.daily_sequence,
  (ready.is_ready_for_dispatch and plan.tracking_status = 'ready'
   and cardinality(plan.tracking_sub_ids) = 4
   and btrim(coalesce(plan.tracking_short_url, '')) <> '') as is_ready_for_dispatch,
  ready.dispatch_status, ready.claim_token, ready.claimed_at, ready.planned_at,
  ready.refresh_status, ready.last_checked_at, ready.age_hours, ready.latest_snapshot_id,
  plan.tracking_sub_ids, plan.tracking_short_url, plan.tracking_generated_at,
  plan.tracking_status, plan.tracking_error, ready.product_cat_id
from offers.v_daily_dispatch_ready ready
join offers.daily_dispatch_plan plan using (dispatch_plan_id);

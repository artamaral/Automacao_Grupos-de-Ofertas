alter table offers.daily_dispatch_plan
  add column if not exists tracking_sub_ids text[];
alter table offers.daily_dispatch_plan
  add column if not exists tracking_short_url text;
alter table offers.daily_dispatch_plan
  add column if not exists tracking_generated_at timestamptz;
alter table offers.daily_dispatch_plan
  add column if not exists tracking_status text not null default 'pending'
    check (tracking_status in ('pending', 'ready', 'failed'));
alter table offers.daily_dispatch_plan
  add column if not exists tracking_error text;

create index if not exists daily_dispatch_plan_tracking_pending_idx
  on offers.daily_dispatch_plan (profile, marketplace, planned_date, tracking_status)
  where dispatch_status = 'planned';

create table if not exists offers.shopee_click_report_imports (
  import_id uuid primary key default gen_random_uuid(),
  source_filename text not null,
  source_sha256 text not null unique check (source_sha256 ~ '^[0-9a-f]{64}$'),
  downloaded_at timestamptz,
  imported_at timestamptz not null default now(),
  row_count integer not null check (row_count >= 0),
  status text not null check (status in ('imported', 'rejected')),
  error text,
  created_at timestamptz not null default now()
);

create table if not exists offers.shopee_click_events (
  click_event_id uuid primary key default gen_random_uuid(),
  import_id uuid not null references offers.shopee_click_report_imports(import_id),
  click_id text not null,
  click_time timestamptz not null,
  click_region text,
  referrer text,
  sub_id_raw text not null,
  tracking_channel text,
  tracking_profile text,
  tracking_dispatch_id text,
  tracking_item_id bigint,
  dispatch_plan_id uuid references offers.daily_dispatch_plan(dispatch_plan_id),
  tracking_parse_status text not null check (
    tracking_parse_status in ('resolved', 'unrecognized', 'legacy_empty')
  ),
  tracking_parse_error text,
  raw_row jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists shopee_click_events_click_id_idx
  on offers.shopee_click_events(click_id);
create index if not exists shopee_click_events_dispatch_plan_idx
  on offers.shopee_click_events(dispatch_plan_id, click_time);

create table if not exists offers.shopee_conversion_sync_runs (
  sync_run_id uuid primary key default gen_random_uuid(),
  report_type text not null default 'conversion_report'
    check (report_type = 'conversion_report'),
  query_filters jsonb not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null check (status in ('running', 'succeeded', 'failed')),
  nodes_received integer not null default 0 check (nodes_received >= 0),
  last_page integer,
  page_limit integer,
  has_next_page boolean,
  last_scroll_id text,
  error text,
  created_at timestamptz not null default now()
);

create table if not exists offers.shopee_conversions (
  conversion_record_id uuid primary key default gen_random_uuid(),
  source_node_key text not null unique check (source_node_key ~ '^[0-9a-f]{64}$'),
  conversion_id text not null,
  dispatch_plan_id uuid references offers.daily_dispatch_plan(dispatch_plan_id),
  utm_content_raw text,
  click_time timestamptz,
  purchase_time timestamptz,
  buyer_type text,
  total_commission numeric,
  net_commission numeric,
  seller_commission numeric,
  shopee_commission_capped numeric,
  raw_payload jsonb not null,
  last_sync_run_id uuid not null references offers.shopee_conversion_sync_runs(sync_run_id),
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists shopee_conversions_conversion_id_idx
  on offers.shopee_conversions(conversion_id);
create index if not exists shopee_conversions_dispatch_plan_idx
  on offers.shopee_conversions(dispatch_plan_id, purchase_time);

create table if not exists offers.shopee_conversion_orders (
  conversion_order_id uuid primary key default gen_random_uuid(),
  conversion_record_id uuid not null references offers.shopee_conversions(conversion_record_id)
    on delete cascade,
  conversion_id text not null,
  order_id text not null,
  shop_type text,
  order_status text,
  raw_payload jsonb not null,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  unique (conversion_record_id, order_id)
);
create index if not exists shopee_conversion_orders_external_idx
  on offers.shopee_conversion_orders(conversion_id, order_id);

create table if not exists offers.shopee_conversion_items (
  conversion_item_id uuid primary key default gen_random_uuid(),
  conversion_order_id uuid not null references offers.shopee_conversion_orders(conversion_order_id)
    on delete cascade,
  conversion_record_id uuid not null references offers.shopee_conversions(conversion_record_id)
    on delete cascade,
  conversion_id text not null,
  order_id text not null,
  item_ordinal integer not null check (item_ordinal >= 0),
  item_id bigint not null,
  item_name text,
  item_price numeric,
  actual_amount numeric,
  refund_amount numeric,
  qty integer,
  item_total_commission numeric,
  global_category_lv1_name text,
  global_category_lv2_name text,
  global_category_lv3_name text,
  fraud_status text,
  attribution_type text,
  complete_time timestamptz,
  raw_payload jsonb not null,
  unique (conversion_order_id, item_ordinal)
);
create index if not exists shopee_conversion_items_item_idx
  on offers.shopee_conversion_items(item_id);

create view offers.v_daily_dispatch_ready_tracked
with (security_invoker = true)
as
select
  ready.dispatch_plan_id, ready.profile, ready.marketplace, ready.stable_key, ready.item_id,
  ready.product_name, plan.tracking_short_url as offer_link, ready.image_url, ready.price,
  ready.reference_price, ready.rating, ready.sales_count, ready.primary_subniche,
  ready.commercial_score, ready.score_reasons, ready.rank_profile, ready.rank_subniche,
  ready.selection_bucket, ready.selection_reason, ready.planned_date, ready.planned_hour,
  ready.slot_sequence, ready.daily_sequence,
  (ready.is_ready_for_dispatch
    and plan.tracking_status = 'ready'
    and cardinality(plan.tracking_sub_ids) = 4
    and btrim(coalesce(plan.tracking_short_url, '')) <> '') as is_ready_for_dispatch,
  ready.dispatch_status, ready.claim_token, ready.claimed_at, ready.planned_at,
  ready.refresh_status, ready.last_checked_at, ready.age_hours, ready.latest_snapshot_id,
  plan.tracking_sub_ids, plan.tracking_short_url, plan.tracking_generated_at,
  plan.tracking_status, plan.tracking_error
from offers.v_daily_dispatch_ready ready
join offers.daily_dispatch_plan plan using (dispatch_plan_id);

create view offers.v_shopee_dispatch_performance
with (security_invoker = true)
as
with publications as (
  select dispatch_plan_id, min(sent_at) as sent_at
  from offers.publication_events
  where delivery_status = 'confirmed' and dispatch_plan_id is not null
  group by dispatch_plan_id
), clicks as (
  select dispatch_plan_id, count(*) as clicks, min(click_time) as first_click_at
  from offers.shopee_click_events where dispatch_plan_id is not null
  group by dispatch_plan_id
), conversions as (
  select dispatch_plan_id, count(*) as conversions,
         sum(coalesce(total_commission, 0)) as total_commission
  from offers.shopee_conversions where dispatch_plan_id is not null
  group by dispatch_plan_id
)
select p.dispatch_plan_id, p.profile, p.marketplace, p.planned_date, p.planned_hour,
       p.daily_sequence, p.item_id as advertised_item_id, p.primary_subniche,
       p.commercial_score, pub.sent_at, coalesce(c.clicks, 0) as clicks,
       coalesce(v.conversions, 0) as conversions,
       coalesce(v.total_commission, 0) as total_commission,
       case when coalesce(c.clicks, 0) > 0 then v.total_commission / c.clicks end
         as total_commission_per_click,
       c.first_click_at - pub.sent_at as time_to_first_click
from offers.daily_dispatch_plan p
left join publications pub using (dispatch_plan_id)
left join clicks c using (dispatch_plan_id)
left join conversions v using (dispatch_plan_id)
where p.marketplace = 'shopee';

create view offers.v_shopee_conversion_item_attribution
with (security_invoker = true)
as
select c.conversion_record_id, c.conversion_id, c.dispatch_plan_id,
       p.item_id as advertised_item_id, i.item_id as purchased_item_id,
       case when i.item_id = p.item_id then 'direct' else 'indirect' end as sale_type,
       i.attribution_type, i.actual_amount, i.item_total_commission,
       i.global_category_lv1_name, i.global_category_lv2_name, i.global_category_lv3_name
from offers.shopee_conversions c
join offers.daily_dispatch_plan p using (dispatch_plan_id)
join offers.shopee_conversion_items i using (conversion_record_id);

create view offers.v_shopee_subniche_performance
with (security_invoker = true)
as
select profile, primary_subniche, count(*) as exposures, sum(clicks) as clicks,
       sum(conversions) as conversions, sum(total_commission) as total_commission,
       avg(total_commission) as total_commission_per_exposure
from offers.v_shopee_dispatch_performance
group by profile, primary_subniche;

alter table offers.shopee_click_report_imports enable row level security;
alter table offers.shopee_click_events enable row level security;
alter table offers.shopee_conversion_sync_runs enable row level security;
alter table offers.shopee_conversions enable row level security;
alter table offers.shopee_conversion_orders enable row level security;
alter table offers.shopee_conversion_items enable row level security;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on offers.shopee_click_report_imports, offers.shopee_click_events,
      offers.shopee_conversion_sync_runs, offers.shopee_conversions,
      offers.shopee_conversion_orders, offers.shopee_conversion_items,
      offers.v_daily_dispatch_ready_tracked, offers.v_shopee_dispatch_performance,
      offers.v_shopee_conversion_item_attribution, offers.v_shopee_subniche_performance
      from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on offers.shopee_click_report_imports, offers.shopee_click_events,
      offers.shopee_conversion_sync_runs, offers.shopee_conversions,
      offers.shopee_conversion_orders, offers.shopee_conversion_items,
      offers.v_daily_dispatch_ready_tracked, offers.v_shopee_dispatch_performance,
      offers.v_shopee_conversion_item_attribution, offers.v_shopee_subniche_performance
      from authenticated;
  end if;
end;
$$;

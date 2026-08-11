create table if not exists offers.candidate_refresh_policies (
  profile text not null check (profile ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  marketplace text not null default 'shopee',
  ttl_hours integer not null default 24 check (ttl_hours >= 24),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (profile, marketplace)
);

insert into offers.candidate_refresh_policies (profile, marketplace, ttl_hours)
values ('feminino', 'shopee', 24)
on conflict (profile, marketplace) do nothing;

drop trigger if exists candidate_refresh_policies_set_updated_at
  on offers.candidate_refresh_policies;

create trigger candidate_refresh_policies_set_updated_at
before update on offers.candidate_refresh_policies
for each row execute function offers.set_updated_at();

create table if not exists offers.offer_snapshots (
  id bigint generated always as identity primary key,
  marketplace text not null default 'shopee',
  item_id bigint not null check (item_id > 0),
  checked_at timestamptz not null,
  shop_id bigint check (shop_id is null or shop_id > 0),
  product_name text,
  product_link text,
  offer_link text,
  image_url text,
  price numeric(14, 2) check (price is null or price > 0),
  price_min numeric(14, 2) check (price_min is null or price_min > 0),
  price_max numeric(14, 2) check (price_max is null or price_max > 0),
  price_discount_rate numeric(7, 3)
    check (price_discount_rate is null or price_discount_rate between 0 and 100),
  commission_rate numeric(9, 6)
    check (commission_rate is null or commission_rate >= 0),
  commission_amount numeric(14, 2)
    check (commission_amount is null or commission_amount >= 0),
  seller_commission_rate numeric(9, 6)
    check (seller_commission_rate is null or seller_commission_rate >= 0),
  shopee_commission_rate numeric(9, 6)
    check (shopee_commission_rate is null or shopee_commission_rate >= 0),
  app_exist_rate numeric(9, 6) check (app_exist_rate is null or app_exist_rate >= 0),
  app_new_rate numeric(9, 6) check (app_new_rate is null or app_new_rate >= 0),
  web_exist_rate numeric(9, 6) check (web_exist_rate is null or web_exist_rate >= 0),
  web_new_rate numeric(9, 6) check (web_new_rate is null or web_new_rate >= 0),
  sales_count bigint check (sales_count is null or sales_count >= 0),
  rating numeric(3, 2) check (rating is null or rating between 0 and 5),
  shop_type_codes smallint[] not null default '{}'::smallint[],
  product_cat_ids bigint[] not null default '{}'::bigint[],
  period_start_time bigint,
  period_end_time bigint,
  source text not null check (btrim(source) <> ''),
  source_payload jsonb not null check (jsonb_typeof(source_payload) = 'object'),
  created_at timestamptz not null default now()
);

create index if not exists offer_snapshots_item_checked_idx
  on offers.offer_snapshots (marketplace, item_id, checked_at desc, id desc);

create index if not exists offer_snapshots_checked_at_idx
  on offers.offer_snapshots (checked_at);

create table if not exists offers.offer_refresh_attempts (
  id bigint generated always as identity primary key,
  profile text not null check (profile ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  marketplace text not null default 'shopee',
  item_id bigint not null check (item_id > 0),
  attempted_at timestamptz not null,
  status text not null
    check (status in ('success', 'technical_failure', 'no_node', 'invalid_payload')),
  snapshot_id bigint references offers.offer_snapshots (id),
  error_type text,
  error_detail text,
  source text not null check (btrim(source) <> ''),
  created_at timestamptz not null default now(),
  check (
    (status = 'success' and snapshot_id is not null)
    or (status <> 'success' and snapshot_id is null)
  )
);

create index if not exists offer_refresh_attempts_item_attempted_idx
  on offers.offer_refresh_attempts (
    profile,
    marketplace,
    item_id,
    attempted_at desc,
    id desc
  );

create or replace view offers.v_offer_latest_snapshot
with (security_invoker = true)
as
select distinct on (snapshot.marketplace, snapshot.item_id)
  snapshot.*
from offers.offer_snapshots snapshot
order by snapshot.marketplace, snapshot.item_id, snapshot.checked_at desc, snapshot.id desc;

create or replace view offers.v_offer_refresh_status
with (security_invoker = true)
as
with active_catalog as (
  select
    item.id as catalog_item_id,
    item.import_id,
    item.profile,
    item.marketplace,
    item.stable_key,
    item.item_id,
    item.product_name,
    item.product_link,
    item.image_url,
    item.subniches,
    item.subniches[1] as primary_subniche,
    item.source_payload
  from offers.catalog_items item
  join offers.catalog_imports imp
    on imp.id = item.import_id
   and imp.status = 'active'
),
latest_attempt as (
  select distinct on (attempt.profile, attempt.marketplace, attempt.item_id)
    attempt.profile,
    attempt.marketplace,
    attempt.item_id,
    attempt.attempted_at as last_attempted_at,
    attempt.status as last_attempt_status
  from offers.offer_refresh_attempts attempt
  order by
    attempt.profile,
    attempt.marketplace,
    attempt.item_id,
    attempt.attempted_at desc,
    attempt.id desc
)
select
  catalog.*,
  policy.ttl_hours,
  snapshot.id as latest_snapshot_id,
  snapshot.checked_at as last_checked_at,
  attempt.last_attempted_at,
  attempt.last_attempt_status,
  case
    when snapshot.id is null then 'MISSING'
    when now() - snapshot.checked_at < make_interval(hours => policy.ttl_hours)
      then 'FRESH'
    else 'STALE'
  end as refresh_status,
  case
    when snapshot.checked_at is null then null
    else extract(epoch from (now() - snapshot.checked_at)) / 3600
  end as age_hours
from active_catalog catalog
join offers.candidate_refresh_policies policy
  on policy.profile = catalog.profile
 and policy.marketplace = catalog.marketplace
left join offers.v_offer_latest_snapshot snapshot
  on snapshot.marketplace = catalog.marketplace
 and snapshot.item_id = catalog.item_id
left join latest_attempt attempt
  on attempt.profile = catalog.profile
 and attempt.marketplace = catalog.marketplace
 and attempt.item_id = catalog.item_id;

create or replace view offers.v_offer_scoring_current
with (security_invoker = true)
as
select
  status.catalog_item_id,
  status.import_id,
  status.profile,
  status.marketplace,
  status.stable_key,
  status.item_id,
  coalesce(snapshot.product_name, status.product_name) as product_name,
  coalesce(snapshot.product_link, status.product_link) as product_link,
  snapshot.offer_link,
  coalesce(snapshot.image_url, status.image_url) as image_url,
  status.subniches,
  status.primary_subniche,
  snapshot.shop_id,
  snapshot.price,
  case
    when snapshot.price_max is not null and snapshot.price_max > snapshot.price
      then snapshot.price_max
    else null
  end as reference_price,
  case
    when snapshot.price_max is not null and snapshot.price_max > snapshot.price
      then round(((snapshot.price_max - snapshot.price) / snapshot.price_max) * 100, 2)
    else 0::numeric
  end as discount_percent,
  case
    when snapshot.seller_commission_rate is not null
      or snapshot.shopee_commission_rate is not null
      then coalesce(snapshot.seller_commission_rate, 0)
         + coalesce(snapshot.shopee_commission_rate, 0)
    else coalesce(snapshot.commission_rate, 0)
  end as commission_rate,
  snapshot.seller_commission_rate,
  snapshot.shopee_commission_rate,
  snapshot.sales_count,
  snapshot.rating,
  snapshot.shop_type_codes,
  case
    when 1 = any(snapshot.shop_type_codes) then 1
    when 4 = any(snapshot.shop_type_codes) then 4
    when 2 = any(snapshot.shop_type_codes) then 2
    else null
  end as shop_type_code,
  null::boolean as is_free_shipping,
  status.last_checked_at,
  status.last_attempted_at,
  status.last_attempt_status,
  status.refresh_status,
  status.age_hours,
  selection.selected_at,
  selection.cooldown_until,
  selection.last_sent_at,
  coalesce(selection.similarity_status, 'not_evaluated') as similarity_status,
  (
    status.refresh_status = 'FRESH'
    and snapshot.price > 0
    and btrim(coalesce(snapshot.offer_link, '')) <> ''
    and snapshot.rating >= 4.8
    and (selection.cooldown_until is null or selection.cooldown_until <= now())
    and coalesce(selection.similarity_status, 'not_evaluated') <> 'suppressed'
  ) as is_scoring_ready
from offers.v_offer_refresh_status status
left join offers.v_offer_latest_snapshot snapshot
  on snapshot.marketplace = status.marketplace
 and snapshot.item_id = status.item_id
left join offers.offer_selection_state selection
  on selection.profile = status.profile
 and selection.marketplace = status.marketplace
 and selection.stable_key = status.stable_key;

comment on table offers.candidate_refresh_policies is
  'Central TTL policy for candidate commercial refresh. Minimum default is 24 hours.';
comment on table offers.offer_snapshots is
  'Append-only observed commercial state from a successful external verification.';
comment on table offers.offer_refresh_attempts is
  'Append-only ledger of real refresh attempts; cache reads do not create rows.';
comment on column offers.offer_snapshots.checked_at is
  'Timestamp when Shopee was actually queried, never when cached data was read.';
comment on column offers.offer_snapshots.source_payload is
  'Auditable request parameters, response node, and pageInfo without credentials.';
comment on view offers.v_offer_latest_snapshot is
  'Latest observed commercial snapshot for each marketplace item.';
comment on view offers.v_offer_refresh_status is
  'Active catalog discovery metadata enriched with profile TTL freshness state.';
comment on view offers.v_offer_scoring_current is
  'Active catalog metadata joined to current commercial state; filter is_scoring_ready before score.';

alter table offers.candidate_refresh_policies enable row level security;
alter table offers.offer_snapshots enable row level security;
alter table offers.offer_refresh_attempts enable row level security;

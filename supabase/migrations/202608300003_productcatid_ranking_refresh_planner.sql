-- Prepared before cutover. The view is empty until the explicit promotion
-- marks the staged generation as catalog_status = 'current'.
do $$
declare
  stage_rows integer;
  stage_categories integer;
  invalid_ratings integer;
  quota_mismatch integer;
  planned_slots integer;
  confirmed_slots integer;
  other_slots integer;
  stable_conflicts integer;
begin
  if (now() at time zone 'America/Sao_Paulo')::time < time '21:00' then
    raise exception 'productCatId cutover requires 21:00 America/Sao_Paulo';
  end if;

  select count(*), count(distinct product_cat_id),
    count(*) filter (where rating < 4.5 or rating is null)
  into stage_rows, stage_categories, invalid_ratings
  from offers.productcatid_import_batch_items
  where batch_id = 'f766c367-26ff-4081-85ba-685b36180f9e';

  with quotas as (
    select product_cat_id, daily_quantity
    from offers.profile_product_category_quotas
    where profile = 'feminino' and marketplace = 'shopee' and enabled
  ), actual as (
    select product_cat_id, count(*) as item_count
    from offers.productcatid_import_batch_items
    where batch_id = 'f766c367-26ff-4081-85ba-685b36180f9e'
    group by product_cat_id
  )
  select count(*) into quota_mismatch
  from quotas
  full join actual using (product_cat_id)
  where quotas.product_cat_id is null
     or actual.product_cat_id is null
     or actual.item_count < quotas.daily_quantity;

  select count(*), count(*) filter (where dispatch_status = 'confirmed'),
    count(*) filter (where dispatch_status <> 'confirmed')
  into planned_slots, confirmed_slots, other_slots
  from offers.daily_dispatch_plan
  where profile = 'feminino'
    and marketplace = 'shopee'
    and planned_date = (now() at time zone 'America/Sao_Paulo')::date;

  select count(*) into stable_conflicts
  from offers.productcatid_import_batch_items stage
  join offers.catalog_items item
    on item.profile = 'feminino'
   and item.marketplace = 'shopee'
   and item.stable_key = stage.stable_key
   and item.item_id <> stage.item_id
  where stage.batch_id = 'f766c367-26ff-4081-85ba-685b36180f9e';

  if stage_rows <> 4511 or stage_categories <> 46 or invalid_ratings <> 0
     or quota_mismatch <> 0 or planned_slots <> 140 or confirmed_slots <> 140
     or other_slots <> 0 or stable_conflicts <> 0 then
    raise exception 'productCatId cutover preflight failed';
  end if;
end $$;

alter table offers.daily_dispatch_plan
  drop constraint if exists daily_dispatch_plan_selection_bucket_check;

alter table offers.daily_dispatch_plan
  add constraint daily_dispatch_plan_selection_bucket_check
  check (selection_bucket in ('fixed_daily', 'weekly_rotation', 'productcatid_exact'));

alter table offers.catalog_item_import_history
  add column if not exists product_cat_id bigint,
  add column if not exists catalog_generation text,
  add column if not exists catalog_status text,
  add column if not exists refresh_required_after timestamptz;

create table if not exists offers.productcatid_cutover_runs (
  id uuid primary key,
  batch_id uuid not null references offers.productcatid_import_batches(id),
  catalog_generation text not null,
  cutover_at timestamptz not null,
  previous_catalog_summary jsonb not null,
  resulting_catalog_summary jsonb,
  created_at timestamptz not null default now()
);

alter table offers.productcatid_cutover_runs enable row level security;

do $$ begin
  revoke all on offers.productcatid_cutover_runs from public;
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on offers.productcatid_cutover_runs from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on offers.productcatid_cutover_runs from authenticated;
  end if;
end $$;

create or replace view offers.v_offer_ranking_productcatid_current
with (security_invoker = true)
as
with catalog_ranking as (
  select
    ranking.*,
    item.product_cat_id,
    item.refresh_required_after,
    (
      ranking.rating >= 4.5
      and ranking.price > 0
      and btrim(coalesce(ranking.offer_link, '')) <> ''
      and (ranking.cooldown_until is null or ranking.cooldown_until <= now())
      and ranking.similarity_status <> 'suppressed'
    ) as is_productcatid_eligible
  from offers.v_offer_ranking_current ranking
  join offers.catalog_items item on item.id = ranking.catalog_item_id
  where item.catalog_status = 'current'
    and item.product_cat_id is not null
), ranked as (
  select
    catalog_ranking.*,
    case when is_productcatid_eligible then
      count(*) filter (where is_productcatid_eligible) over (
        partition by profile, marketplace, product_cat_id
        order by commercial_score desc, sales_count desc, rating desc nulls last, item_id
        rows between unbounded preceding and current row
      )
    end as rank_product_cat
  from catalog_ranking
)
select * from ranked;

comment on view offers.v_offer_ranking_productcatid_current is
  'Current feminino productCatId ranking with 4.5 eligibility; activated only by catalog cutover.';

create or replace view offers.v_daily_dispatch_ready
with (security_invoker = true)
as
select
  plan.dispatch_plan_id, plan.profile, plan.marketplace, plan.stable_key,
  plan.item_id, ranking.product_name, ranking.offer_link, ranking.image_url,
  ranking.price, ranking.reference_price, ranking.rating, ranking.sales_count,
  plan.primary_subniche, plan.commercial_score, ranking.score_reasons,
  ranking.rank_profile, ranking.rank_subniche, plan.selection_bucket,
  plan.selection_reason, plan.planned_date, plan.planned_hour,
  plan.slot_sequence, plan.daily_sequence,
  (plan.dispatch_status = 'planned' and ranking.is_productcatid_eligible
    and ranking.refresh_status = 'FRESH' and ranking.last_checked_at is not null
    and (
      ranking.refresh_required_after is null
      or ranking.last_checked_at >= ranking.refresh_required_after
    )
    and (ranking.last_checked_at at time zone 'America/Sao_Paulo')::date = plan.planned_date)
    as is_ready_for_dispatch,
  plan.dispatch_status, plan.claim_token, plan.claimed_at, plan.created_at as planned_at,
  ranking.refresh_status, ranking.last_checked_at, ranking.age_hours, ranking.latest_snapshot_id,
  ranking.product_cat_id
from offers.daily_dispatch_plan plan
join offers.v_offer_ranking_productcatid_current ranking
  on ranking.profile = plan.profile and ranking.marketplace = plan.marketplace
 and ranking.stable_key = plan.stable_key;

create or replace view offers.v_daily_dispatch_ready_tracked
with (security_invoker = true)
as
select
  ready.dispatch_plan_id, ready.profile, ready.marketplace, ready.stable_key,
  ready.item_id, ready.product_name, plan.tracking_short_url as offer_link,
  ready.image_url, ready.price, ready.reference_price, ready.rating,
  ready.sales_count, ready.primary_subniche, ready.commercial_score,
  ready.score_reasons, ready.rank_profile, ready.rank_subniche,
  ready.selection_bucket, ready.selection_reason, ready.planned_date,
  ready.planned_hour, ready.slot_sequence, ready.daily_sequence,
  (ready.is_ready_for_dispatch and plan.tracking_status = 'ready'
   and cardinality(plan.tracking_sub_ids) = 4
   and btrim(coalesce(plan.tracking_short_url, '')) <> '') as is_ready_for_dispatch,
  ready.dispatch_status, ready.claim_token, ready.claimed_at, ready.planned_at,
  ready.refresh_status, ready.last_checked_at, ready.age_hours, ready.latest_snapshot_id,
  plan.tracking_sub_ids, plan.tracking_short_url, plan.tracking_generated_at,
  plan.tracking_status, plan.tracking_error, ready.product_cat_id
from offers.v_daily_dispatch_ready ready
join offers.daily_dispatch_plan plan using (dispatch_plan_id);

insert into offers.catalog_item_import_history overriding system value
select item.*
from offers.catalog_items item
where item.profile = 'feminino' and item.marketplace = 'shopee'
on conflict do nothing;

with batch as (
  select profile, marketplace, catalog_generation, source_path, source_sha256,
    source_modified_at, observed_at, row_count
  from offers.productcatid_import_batches
  where id = 'f766c367-26ff-4081-85ba-685b36180f9e'
), imported as (
  insert into offers.catalog_imports (
    profile, marketplace, source_path, source_sha256, source_modified_at,
    observed_at, row_count, status, validation_summary
  )
  select profile, marketplace, source_path, source_sha256, source_modified_at,
    observed_at, row_count, 'completed',
    jsonb_build_object(
      'productcatid_batch_id', 'f766c367-26ff-4081-85ba-685b36180f9e',
      'cutover', true
    )
  from batch
  returning id
), legacy as (
  update offers.catalog_items
  set catalog_status = 'legacy'
  where profile = 'feminino' and marketplace = 'shopee'
  returning id
)
insert into offers.catalog_items (
  import_id, profile, marketplace, stable_key, item_id, product_cat_id,
  product_name, product_link, offer_link, image_url, price, reference_price,
  sales_count, rating, shop_type_codes, seller_commission_rate,
  shopee_commission_rate, is_free_shipping, subniches, source_row_number,
  source_payload, catalog_generation, catalog_status, refresh_required_after
)
select (select id from imported), batch.profile, batch.marketplace,
  stage.stable_key, stage.item_id, stage.product_cat_id, stage.product_name,
  stage.product_link, stage.offer_link, stage.image_url, stage.price,
  stage.reference_price, stage.sales_count, stage.rating, stage.shop_type_codes,
  stage.seller_commission_rate, stage.shopee_commission_rate, false,
  stage.subniches, stage.source_row_number, stage.source_payload,
  batch.catalog_generation, 'current', now()
from offers.productcatid_import_batch_items stage
join batch on true
where stage.batch_id = 'f766c367-26ff-4081-85ba-685b36180f9e'
on conflict (profile, marketplace, item_id) do update set
  import_id = excluded.import_id,
  stable_key = excluded.stable_key,
  product_cat_id = excluded.product_cat_id,
  product_name = excluded.product_name,
  product_link = excluded.product_link,
  offer_link = excluded.offer_link,
  image_url = excluded.image_url,
  price = excluded.price,
  reference_price = excluded.reference_price,
  sales_count = excluded.sales_count,
  rating = excluded.rating,
  shop_type_codes = excluded.shop_type_codes,
  seller_commission_rate = excluded.seller_commission_rate,
  shopee_commission_rate = excluded.shopee_commission_rate,
  is_free_shipping = excluded.is_free_shipping,
  subniches = excluded.subniches,
  source_row_number = excluded.source_row_number,
  source_payload = excluded.source_payload,
  catalog_generation = excluded.catalog_generation,
  catalog_status = 'current',
  refresh_required_after = excluded.refresh_required_after;

insert into offers.productcatid_cutover_runs (
  id, batch_id, catalog_generation, cutover_at, previous_catalog_summary,
  resulting_catalog_summary
)
select (
    substr(md5(batch.catalog_generation || now()::text), 1, 8) || '-' ||
    substr(md5(batch.catalog_generation || now()::text), 9, 4) || '-' ||
    substr(md5(batch.catalog_generation || now()::text), 13, 4) || '-' ||
    substr(md5(batch.catalog_generation || now()::text), 17, 4) || '-' ||
    substr(md5(batch.catalog_generation || now()::text), 21, 12)
  )::uuid,
  'f766c367-26ff-4081-85ba-685b36180f9e',
  batch.catalog_generation,
  now(),
  jsonb_build_object('promotion', 'atomic'),
  coalesce((
    select jsonb_object_agg(catalog_status, row_count)
    from (
      select catalog_status, count(*) as row_count
      from offers.catalog_items
      where profile = 'feminino' and marketplace = 'shopee'
      group by catalog_status
    ) statuses
  ), '{}'::jsonb)
from offers.productcatid_import_batches batch
where batch.id = 'f766c367-26ff-4081-85ba-685b36180f9e';

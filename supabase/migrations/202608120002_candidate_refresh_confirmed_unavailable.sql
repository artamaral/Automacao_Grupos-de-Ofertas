alter table offers.offer_refresh_attempts
  drop constraint if exists offer_refresh_attempts_status_check;

alter table offers.offer_refresh_attempts
  add constraint offer_refresh_attempts_status_check
  check (
    status in (
      'success',
      'technical_failure',
      'no_node',
      'invalid_payload',
      'confirmed_unavailable'
    )
  );

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
    when attempt.last_attempt_status = 'confirmed_unavailable'
      and (
        snapshot.checked_at is null
        or snapshot.checked_at <= attempt.last_attempted_at
      )
      then 'UNAVAILABLE_CONFIRMED'
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

comment on view offers.v_offer_refresh_status is
  'Active catalog discovery metadata enriched with profile TTL freshness state and manual unavailable confirmations.';

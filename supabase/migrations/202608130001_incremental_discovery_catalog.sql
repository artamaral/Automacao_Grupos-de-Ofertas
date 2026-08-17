create table if not exists offers.catalog_item_import_history
  (like offers.catalog_items including all);

alter table offers.catalog_item_import_history enable row level security;

insert into offers.catalog_item_import_history overriding system value
select item.*
from offers.catalog_items item
where true
on conflict (import_id, item_id) do nothing;

comment on table offers.catalog_item_import_history is
  'Legacy immutable item rows preserved from catalog imports before incremental discovery.';

delete from offers.catalog_items item
where not exists (
  select 1
  from offers.catalog_imports imp
  where imp.id = item.import_id
    and imp.status = 'active'
);

create unique index if not exists catalog_items_profile_marketplace_item_id_idx
  on offers.catalog_items (profile, marketplace, item_id);

create unique index if not exists catalog_items_profile_marketplace_stable_key_idx
  on offers.catalog_items (profile, marketplace, stable_key);

alter table offers.catalog_imports
  add column if not exists observed_at timestamptz;

update offers.catalog_imports
set observed_at = coalesce(source_modified_at, imported_at)
where observed_at is null;

alter table offers.catalog_imports
  alter column observed_at set not null;

update offers.catalog_imports
set validation_summary = validation_summary || jsonb_build_object(
  'legacy_catalog_status', status,
  'legacy_activated_at', activated_at,
  'legacy_superseded_at', superseded_at
)
where status in ('staged', 'active', 'superseded');

drop function if exists offers.activate_catalog_import(uuid);
drop index if exists offers.catalog_imports_one_active_profile_marketplace_idx;

alter table offers.catalog_imports
  drop constraint if exists catalog_imports_status_check;

update offers.catalog_imports
set status = 'completed'
where status in ('staged', 'active', 'superseded');

alter table offers.catalog_imports
  add constraint catalog_imports_status_check
  check (status in ('completed', 'rejected'));

alter table offers.catalog_imports
  alter column status set default 'completed';

alter table offers.catalog_imports
  drop constraint if exists catalog_imports_profile_marketplace_source_sha256_key;

alter table offers.catalog_imports
  add constraint catalog_imports_profile_marketplace_source_observed_key
  unique (profile, marketplace, source_sha256, observed_at);

alter table offers.offer_snapshots
  add column if not exists catalog_import_id uuid
    references offers.catalog_imports (id);

create unique index if not exists offer_snapshots_catalog_import_item_idx
  on offers.offer_snapshots (catalog_import_id, item_id)
  where catalog_import_id is not null;

create or replace view offers.v_offer_refresh_status
with (security_invoker = true)
as
with persistent_catalog as (
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
from persistent_catalog catalog
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

create or replace view offers.v_offer_ranking_current
with (security_invoker = true)
as
with persistent_catalog as (
  select
    scoring.catalog_item_id,
    scoring.import_id,
    scoring.profile,
    scoring.marketplace,
    scoring.stable_key,
    scoring.item_id,
    scoring.product_name,
    scoring.product_link,
    scoring.offer_link,
    scoring.image_url,
    scoring.price,
    scoring.reference_price,
    scoring.sales_count,
    scoring.rating,
    scoring.shop_type_codes,
    scoring.seller_commission_rate,
    scoring.shopee_commission_rate,
    item.commission_rate_fallback,
    scoring.commission_rate,
    scoring.is_free_shipping,
    scoring.subniches,
    scoring.primary_subniche,
    imp.source_sha256 as catalog_source_sha256,
    imp.imported_at as catalog_imported_at,
    state.selected_at,
    state.cooldown_until,
    state.last_sent_at,
    coalesce(state.selection_count, 0) as selection_count,
    state.selection_reason,
    state.selection_bucket,
    coalesce(state.similarity_status, 'not_evaluated') as similarity_status,
    coalesce(state.refresh_iteration, 0) as refresh_iteration,
    coalesce(state.fields_changed, '{}'::text[]) as fields_changed,
    state.stability_reached,
    state.rescored_at,
    scoring.commercial_data_source,
    scoring.refresh_status,
    scoring.latest_snapshot_id,
    scoring.last_checked_at,
    scoring.age_hours
  from offers.v_offer_scoring_current scoring
  join offers.catalog_items item on item.id = scoring.catalog_item_id
  join offers.catalog_imports imp on imp.id = scoring.import_id
  left join offers.offer_selection_state state
    on state.profile = scoring.profile
   and state.marketplace = scoring.marketplace
   and state.stable_key = scoring.stable_key
),
normalized as (
  select
    persistent_catalog.*,
    case
      when reference_price is not null and reference_price > price
        then round(((reference_price - price) / reference_price) * 100, 2)
      else 0::numeric
    end as discount_percent,
    case
      when 1 = any(shop_type_codes) then 1
      when 4 = any(shop_type_codes) then 4
      when 2 = any(shop_type_codes) then 2
      else null
    end as shop_type_code
  from persistent_catalog
),
components as (
  select
    normalized.*,
    case
      when discount_percent >= 20
        then least(discount_percent, 40) * 0.5
      else 0::numeric
    end as discount_score,
    case when commission_rate > 0 then commission_rate * 100 else 0::numeric end
      as commission_score,
    case
      when sales_count >= 100 then least(sales_count::numeric / 100, 20)
      else 0::numeric
    end as sales_score,
    case when rating >= 4.5 then 10::numeric else 0::numeric end as rating_score,
    case when is_free_shipping then 8::numeric else 0::numeric end as shipping_score,
    case shop_type_code
      when 1 then 10::numeric
      when 4 then 7::numeric
      when 2 then 5::numeric
      else 0::numeric
    end as shop_type_score,
    (
      rating >= 4.8
      and price > 0
      and btrim(coalesce(offer_link, '')) <> ''
      and (cooldown_until is null or cooldown_until <= now())
      and similarity_status <> 'suppressed'
    ) as is_eligible
  from normalized
),
scored as (
  select
    components.*,
    round(
      discount_score + commission_score + sales_score + rating_score
      + shipping_score + shop_type_score,
      2
    ) as commercial_score,
    array_remove(
      array[
        case when discount_score > 0
          then 'desconto de ' || round(discount_percent)::text || '%' end,
        case when commission_score > 0
          then 'comissao de ' || round(commission_rate * 100)::text || '%' end,
        case when sales_score > 0 then sales_count::text || ' vendas' end,
        case when rating_score > 0
          then 'avaliacao ' || to_char(rating, 'FM9.0') end,
        case when shipping_score > 0 then 'frete rapido/gratis' end,
        case shop_type_code
          when 1 then 'loja oficial'
          when 4 then 'loja star+'
          when 2 then 'loja star'
        end
      ],
      null
    )::text[] as score_reasons,
    array_remove(
      array[
        case when rating < 4.8 then 'rating_below_4_8' end,
        case when price <= 0 then 'invalid_price' end,
        case when btrim(coalesce(offer_link, '')) = '' then 'missing_offer_link' end,
        case when cooldown_until is not null and cooldown_until > now()
          then 'cooldown_active' end,
        case when similarity_status = 'suppressed'
          then 'similarity_suppressed' end
      ],
      null
    )::text[] as ineligibility_reasons
  from components
),
ranked as (
  select
    scored.*,
    case when is_eligible then
      count(*) filter (where is_eligible) over (
        partition by profile, marketplace
        order by commercial_score desc, sales_count desc, rating desc nulls last, item_id
        rows between unbounded preceding and current row
      )
    end as computed_rank_profile,
    case when is_eligible then
      count(*) filter (where is_eligible) over (
        partition by profile, marketplace, primary_subniche
        order by commercial_score desc, sales_count desc, rating desc nulls last, item_id
        rows between unbounded preceding and current row
      )
    end as computed_rank_subniche
  from scored
)
select
  ranked.catalog_item_id,
  ranked.import_id,
  ranked.profile,
  ranked.marketplace,
  ranked.stable_key,
  ranked.item_id,
  ranked.product_name,
  ranked.product_link,
  ranked.offer_link,
  ranked.image_url,
  ranked.price,
  ranked.reference_price::numeric(14, 2) as reference_price,
  ranked.sales_count,
  ranked.rating,
  ranked.shop_type_codes,
  ranked.shop_type_code,
  ranked.seller_commission_rate,
  ranked.shopee_commission_rate,
  ranked.commission_rate_fallback,
  ranked.commission_rate,
  ranked.is_free_shipping,
  ranked.subniches,
  ranked.primary_subniche,
  'commercial_v1'::text as score_version,
  ranked.discount_percent,
  round(ranked.discount_score, 2) as discount_score,
  round(ranked.commission_score, 2) as commission_score,
  round(ranked.sales_score, 2) as sales_score,
  round(ranked.rating_score, 2) as rating_score,
  round(ranked.shipping_score, 2) as shipping_score,
  round(ranked.shop_type_score, 2) as shop_type_score,
  ranked.commercial_score,
  ranked.score_reasons,
  ranked.is_eligible,
  ranked.ineligibility_reasons,
  ranked.computed_rank_profile as rank_profile,
  ranked.computed_rank_subniche as rank_subniche,
  ranked.selected_at,
  ranked.cooldown_until,
  ranked.last_sent_at,
  ranked.selection_count,
  ranked.selection_reason,
  ranked.selection_bucket,
  ranked.similarity_status,
  ranked.refresh_iteration,
  ranked.fields_changed,
  ranked.stability_reached,
  ranked.rescored_at,
  ranked.catalog_source_sha256,
  ranked.catalog_imported_at,
  ranked.commercial_data_source,
  ranked.refresh_status,
  ranked.latest_snapshot_id,
  ranked.last_checked_at,
  ranked.age_hours
from ranked;

comment on table offers.catalog_imports is
  'Auditable incremental discovery runs identified by source hash and observation time.';
comment on table offers.catalog_items is
  'Persistent curated catalog; import_id records when an item first entered a profile.';
comment on column offers.catalog_imports.observed_at is
  'Explicit time when the discovery source was observed, used in import idempotency.';
comment on column offers.offer_snapshots.catalog_import_id is
  'Incremental discovery import that produced this snapshot; null for refresh snapshots.';
comment on view offers.v_offer_refresh_status is
  'Persistent catalog discovery metadata enriched with freshness and availability state.';
comment on view offers.v_offer_ranking_current is
  'Ranking commercial_v1 over the persistent catalog using latest commercial snapshots.';

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on offers.catalog_item_import_history from anon;
  end if;

  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on offers.catalog_item_import_history from authenticated;
  end if;
end;
$$;

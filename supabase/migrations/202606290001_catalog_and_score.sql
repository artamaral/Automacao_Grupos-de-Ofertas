create schema if not exists offers;

comment on schema offers is
  'Catalogo curado, estado operacional e ranking de ofertas do projeto.';

create table if not exists offers.schema_migrations (
  migration_name text primary key,
  checksum_sha256 text not null check (checksum_sha256 ~ '^[0-9a-f]{64}$'),
  applied_at timestamptz not null default now()
);

create table if not exists offers.catalog_imports (
  id uuid primary key default gen_random_uuid(),
  profile text not null check (profile ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  marketplace text not null default 'shopee',
  source_path text not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  source_modified_at timestamptz,
  row_count integer not null check (row_count >= 0),
  status text not null default 'staged'
    check (status in ('staged', 'active', 'superseded', 'rejected')),
  validation_summary jsonb not null default '{}'::jsonb
    check (jsonb_typeof(validation_summary) = 'object'),
  imported_by text not null default current_user,
  imported_at timestamptz not null default now(),
  activated_at timestamptz,
  superseded_at timestamptz,
  rejected_at timestamptz,
  rejection_reason text,
  unique (profile, marketplace, source_sha256),
  check (
    (status = 'active' and activated_at is not null)
    or status <> 'active'
  ),
  check (
    (status = 'rejected' and rejected_at is not null and rejection_reason is not null)
    or status <> 'rejected'
  )
);

create unique index if not exists catalog_imports_one_active_profile_marketplace_idx
  on offers.catalog_imports (profile, marketplace)
  where status = 'active';

create index if not exists catalog_imports_profile_imported_at_idx
  on offers.catalog_imports (profile, marketplace, imported_at desc);

create table if not exists offers.catalog_items (
  id bigint generated always as identity primary key,
  import_id uuid not null
    references offers.catalog_imports (id) on delete cascade,
  profile text not null check (profile ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  marketplace text not null default 'shopee',
  stable_key text not null check (stable_key ~ '^[0-9a-f]{64}$'),
  item_id bigint not null check (item_id > 0),
  product_name text not null check (btrim(product_name) <> ''),
  product_link text not null check (btrim(product_link) <> ''),
  offer_link text,
  image_url text,
  price numeric(14, 2) not null check (price > 0),
  reference_price numeric(14, 2) check (reference_price is null or reference_price > 0),
  sales_count bigint not null default 0 check (sales_count >= 0),
  rating numeric(3, 2) check (rating is null or rating between 0 and 5),
  shop_type_codes smallint[] not null default '{}'::smallint[],
  seller_commission_rate numeric(9, 6)
    check (seller_commission_rate is null or seller_commission_rate >= 0),
  shopee_commission_rate numeric(9, 6)
    check (shopee_commission_rate is null or shopee_commission_rate >= 0),
  commission_rate_fallback numeric(9, 6)
    check (commission_rate_fallback is null or commission_rate_fallback >= 0),
  is_free_shipping boolean not null default false,
  subniches text[] not null default '{}'::text[],
  source_row_number integer check (source_row_number is null or source_row_number > 1),
  source_payload jsonb not null default '{}'::jsonb
    check (jsonb_typeof(source_payload) = 'object'),
  created_at timestamptz not null default now(),
  unique (import_id, item_id),
  unique (import_id, stable_key),
  check (reference_price is null or reference_price >= price),
  check (cardinality(subniches) > 0)
);

create index if not exists catalog_items_import_score_inputs_idx
  on offers.catalog_items (
    import_id,
    rating desc,
    sales_count desc,
    price
  );

create index if not exists catalog_items_profile_stable_key_idx
  on offers.catalog_items (profile, marketplace, stable_key);

create index if not exists catalog_items_subniches_gin_idx
  on offers.catalog_items using gin (subniches);

create table if not exists offers.offer_selection_state (
  profile text not null check (profile ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  marketplace text not null default 'shopee',
  stable_key text not null check (stable_key ~ '^[0-9a-f]{64}$'),
  item_id bigint check (item_id is null or item_id > 0),
  selected_at timestamptz,
  cooldown_until timestamptz,
  last_sent_at timestamptz,
  selection_count integer not null default 0 check (selection_count >= 0),
  selection_reason text,
  selection_bucket text,
  similarity_status text not null default 'not_evaluated'
    check (
      similarity_status in (
        'not_evaluated',
        'unique',
        'cluster_winner',
        'suppressed'
      )
    ),
  refresh_iteration integer not null default 0 check (refresh_iteration >= 0),
  fields_changed text[] not null default '{}'::text[],
  stability_reached boolean,
  rescored_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (profile, marketplace, stable_key),
  check (
    selected_at is null
    or cooldown_until is null
    or cooldown_until >= selected_at
  )
);

create index if not exists offer_selection_state_cooldown_idx
  on offers.offer_selection_state (profile, marketplace, cooldown_until);

create or replace function offers.set_updated_at()
returns trigger
language plpgsql
set search_path = pg_catalog
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists offer_selection_state_set_updated_at
  on offers.offer_selection_state;

create trigger offer_selection_state_set_updated_at
before update on offers.offer_selection_state
for each row execute function offers.set_updated_at();

create or replace function offers.activate_catalog_import(p_import_id uuid)
returns offers.catalog_imports
language plpgsql
set search_path = offers, pg_catalog, pg_temp
as $$
declare
  target_import offers.catalog_imports;
begin
  select *
    into target_import
    from offers.catalog_imports
   where id = p_import_id
   for update;

  if not found then
    raise exception 'catalog import % does not exist', p_import_id;
  end if;

  if target_import.status = 'rejected' then
    raise exception 'rejected catalog import % cannot be activated', p_import_id;
  end if;

  update offers.catalog_imports
     set status = 'superseded',
         superseded_at = now()
   where profile = target_import.profile
     and marketplace = target_import.marketplace
     and status = 'active'
     and id <> target_import.id;

  update offers.catalog_imports
     set status = 'active',
         activated_at = coalesce(activated_at, now()),
         superseded_at = null
   where id = target_import.id
   returning * into target_import;

  return target_import;
end;
$$;

create or replace view offers.v_offer_ranking_current
with (security_invoker = true)
as
with active_catalog as (
  select
    ci.id as catalog_item_id,
    ci.import_id,
    ci.profile,
    ci.marketplace,
    ci.stable_key,
    ci.item_id,
    ci.product_name,
    ci.product_link,
    ci.offer_link,
    ci.image_url,
    ci.price,
    ci.reference_price,
    ci.sales_count,
    ci.rating,
    ci.shop_type_codes,
    ci.seller_commission_rate,
    ci.shopee_commission_rate,
    ci.commission_rate_fallback,
    ci.is_free_shipping,
    ci.subniches,
    ci.subniches[1] as primary_subniche,
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
    state.rescored_at
  from offers.catalog_items ci
  join offers.catalog_imports imp
    on imp.id = ci.import_id
   and imp.status = 'active'
  left join offers.offer_selection_state state
    on state.profile = ci.profile
   and state.marketplace = ci.marketplace
   and state.stable_key = ci.stable_key
),
normalized as (
  select
    active_catalog.*,
    case
      when reference_price is not null and reference_price > price
        then round(((reference_price - price) / reference_price) * 100, 2)
      else 0::numeric
    end as discount_percent,
    case
      when seller_commission_rate is not null
        or shopee_commission_rate is not null
        then coalesce(seller_commission_rate, 0)
           + coalesce(shopee_commission_rate, 0)
      else coalesce(commission_rate_fallback, 0)
    end as commission_rate,
    case
      when 1 = any(shop_type_codes) then 1
      when 4 = any(shop_type_codes) then 4
      when 2 = any(shop_type_codes) then 2
      else null
    end as shop_type_code
  from active_catalog
),
components as (
  select
    normalized.*,
    case
      when discount_percent >= 20
        then least(discount_percent, 40) * 0.5
      else 0::numeric
    end as discount_score,
    case
      when commission_rate > 0 then commission_rate * 100
      else 0::numeric
    end as commission_score,
    case
      when sales_count >= 100 then least(sales_count::numeric / 100, 20)
      else 0::numeric
    end as sales_score,
    case
      when rating >= 4.5 then 10::numeric
      else 0::numeric
    end as rating_score,
    case
      when is_free_shipping then 8::numeric
      else 0::numeric
    end as shipping_score,
    case shop_type_code
      when 1 then 10::numeric
      when 4 then 7::numeric
      when 2 then 5::numeric
      else 0::numeric
    end as shop_type_score,
    (
      rating >= 4.8
      and (cooldown_until is null or cooldown_until <= now())
      and similarity_status <> 'suppressed'
    ) as is_eligible
  from normalized
),
scored as (
  select
    components.*,
    round(
      discount_score
      + commission_score
      + sales_score
      + rating_score
      + shipping_score
      + shop_type_score,
      2
    ) as commercial_score,
    array_remove(
      array[
        case
          when discount_score > 0
            then 'desconto de ' || round(discount_percent)::text || '%'
        end,
        case
          when commission_score > 0
            then 'comissao de ' || round(commission_rate * 100)::text || '%'
        end,
        case
          when sales_score > 0 then sales_count::text || ' vendas'
        end,
        case
          when rating_score > 0
            then 'avaliacao ' || to_char(rating, 'FM9.0')
        end,
        case
          when shipping_score > 0 then 'frete rapido/gratis'
        end,
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
        case
          when cooldown_until is not null and cooldown_until > now()
            then 'cooldown_active'
        end,
        case
          when similarity_status = 'suppressed'
            then 'similarity_suppressed'
        end
      ],
      null
    )::text[] as ineligibility_reasons
  from components
),
eligible_ranks as (
  select
    catalog_item_id,
    row_number() over (
      partition by profile, marketplace
      order by
        commercial_score desc,
        sales_count desc,
        rating desc nulls last,
        item_id
    ) as rank_profile,
    row_number() over (
      partition by profile, marketplace, primary_subniche
      order by
        commercial_score desc,
        sales_count desc,
        rating desc nulls last,
        item_id
    ) as rank_subniche
  from scored
  where is_eligible
)
select
  scored.catalog_item_id,
  scored.import_id,
  scored.profile,
  scored.marketplace,
  scored.stable_key,
  scored.item_id,
  scored.product_name,
  scored.product_link,
  scored.offer_link,
  scored.image_url,
  scored.price,
  scored.reference_price,
  scored.sales_count,
  scored.rating,
  scored.shop_type_codes,
  scored.shop_type_code,
  scored.seller_commission_rate,
  scored.shopee_commission_rate,
  scored.commission_rate_fallback,
  scored.commission_rate,
  scored.is_free_shipping,
  scored.subniches,
  scored.primary_subniche,
  'commercial_v1'::text as score_version,
  scored.discount_percent,
  round(scored.discount_score, 2) as discount_score,
  round(scored.commission_score, 2) as commission_score,
  round(scored.sales_score, 2) as sales_score,
  round(scored.rating_score, 2) as rating_score,
  round(scored.shipping_score, 2) as shipping_score,
  round(scored.shop_type_score, 2) as shop_type_score,
  scored.commercial_score,
  scored.score_reasons,
  scored.is_eligible,
  scored.ineligibility_reasons,
  eligible_ranks.rank_profile,
  eligible_ranks.rank_subniche,
  scored.selected_at,
  scored.cooldown_until,
  scored.last_sent_at,
  scored.selection_count,
  scored.selection_reason,
  scored.selection_bucket,
  scored.similarity_status,
  scored.refresh_iteration,
  scored.fields_changed,
  scored.stability_reached,
  scored.rescored_at,
  scored.catalog_source_sha256,
  scored.catalog_imported_at
from scored
left join eligible_ranks using (catalog_item_id);

comment on table offers.catalog_imports is
  'Registro auditavel de cada catalogo local validado e publicado.';
comment on table offers.catalog_items is
  'Snapshot imutavel dos itens pertencentes a uma importacao de catalogo.';
comment on table offers.offer_selection_state is
  'Estado operacional por oferta e profile, separado do snapshot do catalogo.';
comment on view offers.v_offer_ranking_current is
  'Ranking commercial_v1 do catalogo ativo, com componentes, motivos e controles.';

alter table offers.schema_migrations enable row level security;
alter table offers.catalog_imports enable row level security;
alter table offers.catalog_items enable row level security;
alter table offers.offer_selection_state enable row level security;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on schema offers from anon;
    revoke all on all tables in schema offers from anon;
    revoke all on all sequences in schema offers from anon;
    revoke execute on all functions in schema offers from anon;
  end if;

  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on schema offers from authenticated;
    revoke all on all tables in schema offers from authenticated;
    revoke all on all sequences in schema offers from authenticated;
    revoke execute on all functions in schema offers from authenticated;
  end if;
end;
$$;

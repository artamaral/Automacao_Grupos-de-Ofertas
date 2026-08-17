create or replace view offers.v_offer_scoring_current
with (security_invoker = true)
as
with resolved as (
  select
    status.catalog_item_id,
    status.import_id,
    status.profile,
    status.marketplace,
    status.stable_key,
    status.item_id,
    coalesce(snapshot.product_name, item.product_name) as product_name,
    coalesce(snapshot.product_link, item.product_link) as product_link,
    coalesce(snapshot.offer_link, item.offer_link) as offer_link,
    coalesce(snapshot.image_url, item.image_url) as image_url,
    item.subniches,
    item.subniches[1] as primary_subniche,
    snapshot.shop_id,
    coalesce(snapshot.price, item.price) as price,
    (case
      when snapshot.id is null then item.reference_price
      when snapshot.price_max is null then item.reference_price
      when snapshot.price_max > coalesce(snapshot.price, item.price) then snapshot.price_max
      else null
    end)::numeric(14, 2) as reference_price,
    case
      when snapshot.id is not null
       and (snapshot.seller_commission_rate is not null
         or snapshot.shopee_commission_rate is not null)
        then coalesce(snapshot.seller_commission_rate, 0)
           + coalesce(snapshot.shopee_commission_rate, 0)
      when snapshot.id is not null and snapshot.commission_rate is not null
        then snapshot.commission_rate
      when item.seller_commission_rate is not null
        or item.shopee_commission_rate is not null
        then coalesce(item.seller_commission_rate, 0)
           + coalesce(item.shopee_commission_rate, 0)
      else coalesce(item.commission_rate_fallback, 0)
    end as commission_rate,
    coalesce(snapshot.seller_commission_rate, item.seller_commission_rate)
      as seller_commission_rate,
    coalesce(snapshot.shopee_commission_rate, item.shopee_commission_rate)
      as shopee_commission_rate,
    coalesce(snapshot.sales_count, item.sales_count) as sales_count,
    coalesce(snapshot.rating, item.rating) as rating,
    case
      when snapshot.id is not null and cardinality(snapshot.shop_type_codes) > 0
        then snapshot.shop_type_codes
      else item.shop_type_codes
    end as shop_type_codes,
    case when snapshot.id is null then item.is_free_shipping else null::boolean end
      as is_free_shipping,
    status.last_checked_at,
    status.last_attempted_at,
    status.last_attempt_status,
    status.refresh_status,
    status.age_hours,
    selection.selected_at,
    selection.cooldown_until,
    selection.last_sent_at,
    coalesce(selection.similarity_status, 'not_evaluated') as similarity_status,
    case when snapshot.id is null then 'catalog' else 'snapshot' end
      as commercial_data_source,
    snapshot.id as latest_snapshot_id
  from offers.v_offer_refresh_status status
  join offers.catalog_items item on item.id = status.catalog_item_id
  left join offers.v_offer_latest_snapshot snapshot
    on snapshot.marketplace = status.marketplace
   and snapshot.item_id = status.item_id
  left join offers.offer_selection_state selection
    on selection.profile = status.profile
   and selection.marketplace = status.marketplace
   and selection.stable_key = status.stable_key
)
select
  resolved.catalog_item_id,
  resolved.import_id,
  resolved.profile,
  resolved.marketplace,
  resolved.stable_key,
  resolved.item_id,
  resolved.product_name,
  resolved.product_link,
  resolved.offer_link,
  resolved.image_url,
  resolved.subniches,
  resolved.primary_subniche,
  resolved.shop_id,
  resolved.price,
  resolved.reference_price::numeric as reference_price,
  case
    when resolved.reference_price is not null
     and resolved.reference_price > resolved.price
      then round(
        ((resolved.reference_price - resolved.price) / resolved.reference_price) * 100,
        2
      )
    else 0::numeric
  end as discount_percent,
  resolved.commission_rate,
  resolved.seller_commission_rate,
  resolved.shopee_commission_rate,
  resolved.sales_count,
  resolved.rating,
  resolved.shop_type_codes,
  case
    when 1 = any(resolved.shop_type_codes) then 1
    when 4 = any(resolved.shop_type_codes) then 4
    when 2 = any(resolved.shop_type_codes) then 2
    else null
  end as shop_type_code,
  resolved.is_free_shipping,
  resolved.last_checked_at,
  resolved.last_attempted_at,
  resolved.last_attempt_status,
  resolved.refresh_status,
  resolved.age_hours,
  resolved.selected_at,
  resolved.cooldown_until,
  resolved.last_sent_at,
  resolved.similarity_status,
  (
    resolved.price > 0
    and btrim(coalesce(resolved.offer_link, '')) <> ''
    and resolved.rating >= 4.8
    and (resolved.cooldown_until is null or resolved.cooldown_until <= now())
    and resolved.similarity_status <> 'suppressed'
  ) as is_scoring_ready,
  resolved.commercial_data_source,
  resolved.latest_snapshot_id
from resolved;

create or replace view offers.v_offer_ranking_current
with (security_invoker = true)
as
with active_catalog as (
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
  join offers.catalog_imports imp
    on imp.id = scoring.import_id
   and imp.status = 'active'
  left join offers.offer_selection_state state
    on state.profile = scoring.profile
   and state.marketplace = scoring.marketplace
   and state.stable_key = scoring.stable_key
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
eligible_ranks as (
  select
    catalog_item_id,
    row_number() over (
      partition by profile, marketplace
      order by commercial_score desc, sales_count desc, rating desc nulls last, item_id
    ) as rank_profile,
    row_number() over (
      partition by profile, marketplace, primary_subniche
      order by commercial_score desc, sales_count desc, rating desc nulls last, item_id
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
  scored.reference_price::numeric(14, 2) as reference_price,
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
  scored.catalog_imported_at,
  scored.commercial_data_source,
  scored.refresh_status,
  scored.latest_snapshot_id,
  scored.last_checked_at,
  scored.age_hours
from scored
left join eligible_ranks using (catalog_item_id);

comment on view offers.v_offer_scoring_current is
  'Active catalog resolved with the latest commercial snapshot and catalog fallback.';
comment on view offers.v_offer_ranking_current is
  'Ranking commercial_v1 using latest snapshots when available and catalog fallback otherwise.';

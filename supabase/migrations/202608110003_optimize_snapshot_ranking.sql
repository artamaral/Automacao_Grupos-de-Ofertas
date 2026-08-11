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

comment on view offers.v_offer_ranking_current is
  'Ranking commercial_v1 using latest snapshots with single-pass conditional ranks.';

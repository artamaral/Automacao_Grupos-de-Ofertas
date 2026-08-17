create or replace view offers.v_instagram_dispatch_ready
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
  ranking.price,
  ranking.rating,
  plan.primary_subniche,
  ranking.score_reasons,
  plan.selection_bucket,
  plan.selection_reason,
  media.product_link,
  media.shop_id,
  media.image_urls,
  media.video_url,
  media.resolved_at as media_resolved_at,
  media.last_checked_at as media_last_checked_at,
  format.instagram_format,
  plan.planned_date,
  plan.planned_hour,
  plan.slot_sequence,
  plan.daily_sequence,
  plan.created_at as planned_at,
  concat_ws(
    E'\n\n',
    concat_ws(
      E'\n',
      '🔥 ' || ranking.product_name,
      nullif(btrim(coalesce(ranking.offer_link, '')), '')
    ),
    concat_ws(
      E'\n',
      case when ranking.price is not null then '💸 R$ ' || ranking.price::text end,
      case when ranking.rating is not null then '⭐ ' || ranking.rating::text || '/5 na Shopee' end
    ),
    '⚠️ Preco e disponibilidade podem mudar.',
    '#ad #shopee #' ||
      coalesce(
        nullif(
          regexp_replace(
            lower(coalesce(plan.primary_subniche, 'ofertas')),
            '[^a-z0-9]+',
            '',
            'g'
          ),
          ''
        ),
        'ofertas'
      ) ||
      ' #achadinhos'
  ) as caption_base,
  ranking.refresh_status,
  ranking.is_eligible,
  ranking.ineligibility_reasons
from offers.daily_dispatch_plan plan
join offers.v_offer_ranking_current ranking
  on ranking.profile = plan.profile
 and ranking.marketplace = plan.marketplace
 and ranking.stable_key = plan.stable_key
join offers.offer_media_assets media
  on media.profile = plan.profile
 and media.marketplace = plan.marketplace
 and media.item_id = plan.item_id
cross join lateral (
  select 'reels'::text as instagram_format
  where media.video_url is not null
  union all
  select 'carousel'::text as instagram_format
  where jsonb_array_length(media.image_urls) > 0
) format
where plan.dispatch_status = 'planned'
  and media.status = 'valid'
order by
  plan.planned_date,
  plan.daily_sequence,
  format.instagram_format desc;

comment on view offers.v_instagram_dispatch_ready is
  'Superficie pronta para o workflow Instagram; usa a fila persistida e a midia valida, sem depender da prontidao operacional do WhatsApp/base ready.';

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on offers.v_instagram_dispatch_ready from anon;
  end if;

  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on offers.v_instagram_dispatch_ready from authenticated;
  end if;
end;
$$;

create or replace view offers.v_instagram_dispatch_ready
with (security_invoker = true)
as
select
  ready.dispatch_plan_id,
  ready.profile,
  ready.marketplace,
  ready.stable_key,
  ready.item_id,
  ready.product_name,
  ready.offer_link,
  ready.price,
  ready.rating,
  ready.primary_subniche,
  ready.score_reasons,
  ready.selection_bucket,
  ready.selection_reason,
  media.product_link,
  media.shop_id,
  media.image_urls,
  media.video_url,
  media.resolved_at as media_resolved_at,
  media.last_checked_at as media_last_checked_at,
  format.instagram_format,
  ready.planned_date,
  ready.planned_hour,
  ready.slot_sequence,
  ready.daily_sequence,
  ready.planned_at,
  concat_ws(
    E'\n\n',
    concat_ws(
      E'\n',
      '🔥 ' || ready.product_name,
      nullif(btrim(coalesce(ready.offer_link, '')), '')
    ),
    concat_ws(
      E'\n',
      case when ready.price is not null then '💸 R$ ' || ready.price::text end,
      case when ready.rating is not null then '⭐ ' || ready.rating::text || '/5 na Shopee' end
    ),
    '⚠️ Preco e disponibilidade podem mudar.',
    '#ad #shopee #' ||
      coalesce(
        nullif(
          regexp_replace(
            lower(coalesce(ready.primary_subniche, 'ofertas')),
            '[^a-z0-9]+',
            '',
            'g'
          ),
          ''
        ),
        'ofertas'
      ) ||
      ' #achadinhos'
  ) as caption_base
from offers.v_daily_dispatch_ready ready
join offers.offer_media_assets media
  on media.profile = ready.profile
 and media.marketplace = ready.marketplace
 and media.item_id = ready.item_id
cross join lateral (
  select 'reels'::text as instagram_format
  where media.video_url is not null
  union all
  select 'carousel'::text as instagram_format
  where jsonb_array_length(media.image_urls) > 0
) format
where ready.is_ready_for_dispatch
  and media.status = 'valid'
order by
  ready.planned_date,
  ready.planned_hour,
  ready.slot_sequence,
  ready.daily_sequence,
  format.instagram_format desc;

comment on view offers.v_instagram_dispatch_ready is
  'Superficie pronta para o workflow Instagram; junta fila diaria e midias ja resolvidas, sem recalcular selecao.';

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

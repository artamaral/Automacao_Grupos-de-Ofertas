create table if not exists offers.offer_media_assets (
  media_asset_id uuid primary key default gen_random_uuid(),
  profile text not null check (profile ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  marketplace text not null default 'shopee' check (btrim(marketplace) <> ''),
  item_id bigint not null check (item_id > 0),
  shop_id bigint check (shop_id is null or shop_id > 0),
  product_link text not null check (btrim(product_link) <> ''),
  image_urls jsonb not null default '[]'::jsonb check (jsonb_typeof(image_urls) = 'array'),
  video_url text,
  source text not null default 'shopee_product_html' check (btrim(source) <> ''),
  status text not null check (status in ('valid', 'no_media', 'failed', 'stale')),
  resolved_at timestamptz not null default now(),
  last_checked_at timestamptz not null default now(),
  error_detail text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (profile, marketplace, item_id),
  check (
    status <> 'valid'
    or video_url is not null
    or jsonb_array_length(image_urls) > 0
  )
);

create index if not exists offer_media_assets_status_idx
  on offers.offer_media_assets (profile, marketplace, status, last_checked_at desc);

create index if not exists offer_media_assets_reels_ready_idx
  on offers.offer_media_assets (profile, marketplace, last_checked_at desc)
  where status = 'valid' and video_url is not null;

create index if not exists offer_media_assets_carousel_ready_idx
  on offers.offer_media_assets (profile, marketplace, last_checked_at desc)
  where status = 'valid' and jsonb_array_length(image_urls) > 0;

drop trigger if exists offer_media_assets_set_updated_at
  on offers.offer_media_assets;

create trigger offer_media_assets_set_updated_at
before update on offers.offer_media_assets
for each row execute function offers.set_updated_at();

comment on table offers.offer_media_assets is
  'Midias publicas resolvidas do anuncio para consumo do workflow Instagram; nao armazena arquivos.';

comment on column offers.offer_media_assets.image_urls is
  'Lista ordenada de imagens validas do anuncio Shopee, preservando a ordem da galeria.';

comment on column offers.offer_media_assets.video_url is
  'Primeira URL de video valida resolvida para Reels quando disponivel.';

alter table offers.offer_media_assets enable row level security;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on offers.offer_media_assets from anon;
  end if;

  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on offers.offer_media_assets from authenticated;
  end if;
end;
$$;

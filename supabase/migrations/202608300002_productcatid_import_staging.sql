-- This is an import-audit area, not a second operational catalog.  Its rows
-- are inert until the explicit post-21:00 cutover promotes them into
-- offers.catalog_items.
create table if not exists offers.productcatid_import_batches (
  id uuid primary key,
  profile text not null,
  marketplace text not null,
  catalog_generation text not null,
  source_path text not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  source_modified_at timestamptz not null,
  observed_at timestamptz not null,
  row_count integer not null check (row_count > 0),
  validation_summary jsonb not null,
  staged_at timestamptz not null default now(),
  unique (profile, marketplace, catalog_generation)
);

create table if not exists offers.productcatid_import_batch_items (
  batch_id uuid not null references offers.productcatid_import_batches(id) on delete cascade,
  stable_key text not null,
  item_id bigint not null check (item_id > 0),
  product_cat_id bigint not null references offers.shopee_product_categories(category_id),
  product_name text not null,
  product_link text not null,
  offer_link text,
  image_url text,
  price numeric(14, 2) not null check (price > 0),
  reference_price numeric(14, 2),
  sales_count bigint not null,
  rating numeric(3, 2) not null check (rating >= 4.5),
  shop_type_codes smallint[] not null,
  seller_commission_rate numeric(9, 6),
  shopee_commission_rate numeric(9, 6),
  subniches text[] not null default '{}',
  source_row_number integer not null,
  source_payload jsonb not null,
  primary key (batch_id, item_id),
  unique (batch_id, stable_key)
);

create index if not exists productcatid_import_batch_items_category_idx
  on offers.productcatid_import_batch_items(batch_id, product_cat_id);

alter table offers.productcatid_import_batches enable row level security;
alter table offers.productcatid_import_batch_items enable row level security;

do $$ begin
  revoke all on offers.productcatid_import_batches, offers.productcatid_import_batch_items from public;
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on offers.productcatid_import_batches, offers.productcatid_import_batch_items from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on offers.productcatid_import_batches, offers.productcatid_import_batch_items from authenticated;
  end if;
end $$;

comment on table offers.productcatid_import_batches is
  'Inert validated productCatId import batches, retained only until the explicit catalog cutover.';
comment on table offers.productcatid_import_batch_items is
  'Validated source rows for an inert productCatId import batch; never consumed by ranking, refresh, planner, or n8n.';

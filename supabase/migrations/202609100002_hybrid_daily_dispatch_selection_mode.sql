do $$
declare
  missing_categories bigint[];
begin
  select array_agg(matrix.product_cat_id order by matrix.product_cat_id)
  into missing_categories
  from (
    values
      (100104::bigint), (100350), (101669), (100352), (100360),
      (100382), (102032), (101670), (100361), (100095),
      (100102), (100353), (100338)
  ) as matrix(product_cat_id)
  left join offers.shopee_product_categories category
    on category.category_id = matrix.product_cat_id
  where category.category_id is null;

  if missing_categories is not null then
    raise exception 'hybrid quota categories absent from taxonomy: %', missing_categories;
  end if;
end
$$;

update offers.profile_product_category_quotas
set enabled = false, updated_at = now()
where profile = 'feminino'
  and marketplace = 'shopee'
  and enabled;

insert into offers.profile_product_category_quotas (
  profile,
  marketplace,
  product_cat_id,
  daily_quantity,
  enabled,
  source_sha256,
  updated_at
)
values
  ('feminino', 'shopee', 100104, 10, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 100350, 9, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 101669, 8, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 100352, 8, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 100360, 7, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 100382, 7, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 102032, 7, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 101670, 6, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 100361, 4, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 100095, 3, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 100102, 3, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 100353, 3, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now()),
  ('feminino', 'shopee', 100338, 3, true, '1b0f6dba4e32748c3f1931e4088ff761b39fa60dc7381aab4eab5ff5e604b9c4', now())
on conflict (profile, marketplace, product_cat_id) do update set
  daily_quantity = excluded.daily_quantity,
  enabled = excluded.enabled,
  source_sha256 = excluded.source_sha256,
  updated_at = excluded.updated_at;

alter table offers.daily_dispatch_plan
  drop constraint if exists daily_dispatch_plan_selection_bucket_check;

alter table offers.daily_dispatch_plan
  add constraint daily_dispatch_plan_selection_bucket_check
  check (
    selection_bucket in (
      'fixed_daily',
      'weekly_rotation',
      'productcatid_exact',
      'user_defined_rank'
    )
  );

alter table offers.catalog_item_import_history
  add column if not exists selection_mode text;

do $$
declare
  enabled_categories integer;
  enabled_slots integer;
  invalid_enabled integer;
begin
  select count(*), coalesce(sum(daily_quantity), 0)
  into enabled_categories, enabled_slots
  from offers.profile_product_category_quotas
  where profile = 'feminino'
    and marketplace = 'shopee'
    and enabled;

  select count(*)
  into invalid_enabled
  from offers.profile_product_category_quotas
  where profile = 'feminino'
    and marketplace = 'shopee'
    and enabled
    and product_cat_id not in (
      100104, 100350, 101669, 100352, 100360, 100382, 102032,
      101670, 100361, 100095, 100102, 100353, 100338
    );

  if enabled_categories <> 13 or enabled_slots <> 78 or invalid_enabled <> 0 then
    raise exception
      'hybrid quota validation failed: categories=% slots=% invalid=%',
      enabled_categories,
      enabled_slots,
      invalid_enabled;
  end if;
end
$$;

comment on column offers.catalog_item_import_history.selection_mode is
  'Catalog origin copied from catalog_items during productCatId cutover history archival.';

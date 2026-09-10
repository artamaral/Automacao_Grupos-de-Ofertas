alter table offers.catalog_items
  add column if not exists selection_mode text;

alter table offers.catalog_items
  add constraint catalog_items_selection_mode_check
  check (selection_mode in ('productCatId', 'user_defined'));

do $$
declare
  automatic_current_count integer;
  manual_import_row_count integer;
  manual_catalog_item_count integer;
  manual_invalid_count integer;
begin
  select imp.row_count
  into manual_import_row_count
  from offers.catalog_imports imp
  where imp.id = '503a3436-7a36-41fb-9303-1aee43e8d978'::uuid
    and imp.profile = 'feminino'
    and imp.marketplace = 'shopee'
    and imp.status = 'completed';

  if manual_import_row_count is distinct from 311 then
    raise exception
      'manual catalog import preflight failed: expected completed import with 311 rows, got %',
      manual_import_row_count;
  end if;

  select count(*)
  into automatic_current_count
  from offers.catalog_items item
  where item.profile = 'feminino'
    and item.marketplace = 'shopee'
    and item.catalog_status = 'current';

  if automatic_current_count <> 4511 then
    raise exception
      'automatic catalog preflight failed: expected 4511 current items, got %',
      automatic_current_count;
  end if;

  select
    count(*),
    count(*) filter (
      where item.catalog_status <> 'legacy'
         or item.product_cat_id is null
         or item.selection_mode is not null
    )
  into manual_catalog_item_count, manual_invalid_count
  from offers.catalog_items item
  where item.import_id = '503a3436-7a36-41fb-9303-1aee43e8d978'::uuid
    and item.profile = 'feminino'
    and item.marketplace = 'shopee';

  if manual_catalog_item_count <> 311 or manual_invalid_count <> 0 then
    raise exception
      'manual catalog item preflight failed: expected 311 legacy unclassified items with productCatId, got rows=% invalid=%',
      manual_catalog_item_count,
      manual_invalid_count;
  end if;
end
$$;

update offers.catalog_items item
set selection_mode = 'productCatId'
where item.profile = 'feminino'
  and item.marketplace = 'shopee'
  and item.catalog_status = 'current'
  and item.selection_mode is null;

update offers.catalog_items item
set
  selection_mode = 'user_defined',
  catalog_status = 'current'
where item.import_id = '503a3436-7a36-41fb-9303-1aee43e8d978'::uuid
  and item.profile = 'feminino'
  and item.marketplace = 'shopee'
  and item.catalog_status = 'legacy'
  and item.selection_mode is null;

create index if not exists catalog_items_current_selection_mode_idx
  on offers.catalog_items (profile, marketplace, selection_mode)
  where catalog_status = 'current' and selection_mode is not null;

comment on column offers.catalog_items.selection_mode is
  'Immutable catalog origin: productCatId for automatic category discovery or user_defined for manual itemId discovery; legacy unclassified rows remain null.';

do $$
declare
  automatic_count integer;
  manual_count integer;
  current_null_count integer;
  current_total integer;
  legacy_classified_count integer;
begin
  select
    count(*) filter (where item.selection_mode = 'productCatId'),
    count(*) filter (where item.selection_mode = 'user_defined'),
    count(*) filter (where item.selection_mode is null),
    count(*)
  into automatic_count, manual_count, current_null_count, current_total
  from offers.catalog_items item
  where item.profile = 'feminino'
    and item.marketplace = 'shopee'
    and item.catalog_status = 'current';

  select count(*)
  into legacy_classified_count
  from offers.catalog_items item
  where item.profile = 'feminino'
    and item.marketplace = 'shopee'
    and item.catalog_status = 'legacy'
    and item.selection_mode is not null;

  if automatic_count <> 4511
     or manual_count <> 311
     or current_null_count <> 0
     or current_total <> 4822
     or legacy_classified_count <> 0 then
    raise exception
      'catalog selection mode validation failed: automatic=% manual=% current_null=% current_total=% legacy_classified=%',
      automatic_count,
      manual_count,
      current_null_count,
      current_total,
      legacy_classified_count;
  end if;
end
$$;

begin;

alter table offers.catalog_items
  drop constraint if exists catalog_items_profile_check;

alter table offers.catalog_items
  add constraint catalog_items_profile_check
  check (profile ~ '^[a-z0-9]+(?:[-_][a-z0-9]+)*$');

commit;

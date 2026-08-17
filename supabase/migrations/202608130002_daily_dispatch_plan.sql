create table if not exists offers.daily_dispatch_plan (
  dispatch_plan_id uuid primary key default gen_random_uuid(),
  profile text not null check (profile ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  marketplace text not null default 'shopee',
  stable_key text not null check (stable_key ~ '^[0-9a-f]{64}$'),
  item_id bigint not null check (item_id > 0),
  primary_subniche text not null check (btrim(primary_subniche) <> ''),
  commercial_score numeric(14, 4) not null,
  selection_bucket text not null check (
    selection_bucket in ('fixed_daily', 'weekly_rotation')
  ),
  selection_reason text not null check (btrim(selection_reason) <> ''),
  planned_date date not null,
  planned_hour smallint not null check (planned_hour between 0 and 23),
  slot_sequence smallint not null check (slot_sequence between 1 and 8),
  daily_sequence smallint not null check (daily_sequence between 1 and 112),
  dispatch_status text not null default 'planned' check (
    dispatch_status in ('planned', 'claimed', 'confirmed', 'failed', 'cancelled')
  ),
  claim_token text,
  claimed_at timestamptz,
  publication_event_id uuid references offers.publication_events (publish_id),
  consumed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (profile, marketplace, planned_date, stable_key),
  unique (profile, marketplace, planned_date, daily_sequence),
  unique (profile, marketplace, planned_date, planned_hour, slot_sequence),
  check (
    (
      dispatch_status = 'planned'
      and claim_token is null
      and claimed_at is null
      and publication_event_id is null
      and consumed_at is null
    )
    or (
      dispatch_status = 'claimed'
      and btrim(coalesce(claim_token, '')) <> ''
      and claimed_at is not null
      and publication_event_id is null
      and consumed_at is null
    )
    or (
      dispatch_status in ('confirmed', 'failed', 'cancelled')
      and btrim(coalesce(claim_token, '')) <> ''
      and claimed_at is not null
      and publication_event_id is not null
      and consumed_at is not null
    )
  )
);

create index if not exists daily_dispatch_plan_ready_window_idx
  on offers.daily_dispatch_plan (
    profile, marketplace, planned_date, planned_hour, slot_sequence
  )
  where dispatch_status = 'planned';

create index if not exists daily_dispatch_plan_weekly_coverage_idx
  on offers.daily_dispatch_plan (profile, planned_date, selection_bucket, primary_subniche);

alter table offers.publication_events
  add column if not exists dispatch_plan_id uuid
    references offers.daily_dispatch_plan (dispatch_plan_id);

create unique index if not exists publication_events_dispatch_plan_id_idx
  on offers.publication_events (dispatch_plan_id)
  where dispatch_plan_id is not null;

create or replace function offers.sync_daily_dispatch_status()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if new.dispatch_plan_id is null then
    return new;
  end if;

  update offers.daily_dispatch_plan
  set dispatch_status = new.delivery_status,
      publication_event_id = new.publish_id,
      consumed_at = coalesce(new.sent_at, now()),
      updated_at = now()
  where dispatch_plan_id = new.dispatch_plan_id;

  return new;
end;
$$;

drop trigger if exists publication_events_sync_daily_dispatch_status
  on offers.publication_events;

create trigger publication_events_sync_daily_dispatch_status
after insert or update of delivery_status, sent_at
on offers.publication_events
for each row execute function offers.sync_daily_dispatch_status();

drop trigger if exists daily_dispatch_plan_set_updated_at
  on offers.daily_dispatch_plan;

create trigger daily_dispatch_plan_set_updated_at
before update on offers.daily_dispatch_plan
for each row execute function offers.set_updated_at();

create or replace view offers.v_daily_dispatch_ready
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
  ranking.image_url,
  ranking.price,
  ranking.reference_price,
  ranking.rating,
  ranking.sales_count,
  plan.primary_subniche,
  plan.commercial_score,
  ranking.score_reasons,
  ranking.rank_profile,
  ranking.rank_subniche,
  plan.selection_bucket,
  plan.selection_reason,
  plan.planned_date,
  plan.planned_hour,
  plan.slot_sequence,
  plan.daily_sequence,
  (plan.dispatch_status = 'planned' and ranking.is_eligible) as is_ready_for_dispatch,
  plan.dispatch_status,
  plan.claim_token,
  plan.claimed_at,
  plan.created_at as planned_at
from offers.daily_dispatch_plan plan
join offers.v_offer_ranking_current ranking
  on ranking.profile = plan.profile
 and ranking.marketplace = plan.marketplace
 and ranking.stable_key = plan.stable_key;

comment on table offers.daily_dispatch_plan is
  'Fila diaria persistida: 112 itens do feminino em 14 janelas, preparada antes do n8n.';
comment on view offers.v_daily_dispatch_ready is
  'Superficie operacional pronta; n8n filtra data e hora sem recalcular bandas.';
comment on column offers.publication_events.dispatch_plan_id is
  'Slot planejado que originou a tentativa, usado para consumo idempotente da fila.';

alter table offers.daily_dispatch_plan enable row level security;

do $$
begin
  revoke all on function offers.sync_daily_dispatch_status() from public;

  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on offers.daily_dispatch_plan from anon;
    revoke all on offers.v_daily_dispatch_ready from anon;
    revoke execute on function offers.sync_daily_dispatch_status() from anon;
  end if;

  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on offers.daily_dispatch_plan from authenticated;
    revoke all on offers.v_daily_dispatch_ready from authenticated;
    revoke execute on function offers.sync_daily_dispatch_status() from authenticated;
  end if;
end;
$$;

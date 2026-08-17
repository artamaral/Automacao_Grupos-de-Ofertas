create table if not exists offers.publication_events (
  publish_id uuid primary key default gen_random_uuid(),
  profile text not null check (length(trim(profile)) > 0),
  marketplace text not null check (length(trim(marketplace)) > 0),
  stable_key text not null check (stable_key ~ '^[0-9a-f]{64}$'),
  item_id bigint,
  target text not null check (length(trim(target)) > 0),
  channel_adapter text not null check (length(trim(channel_adapter)) > 0),
  delivery_status text not null default 'confirmed' check (
    delivery_status in ('confirmed', 'failed', 'cancelled')
  ),
  manifest_item_number integer not null check (manifest_item_number > 0),
  artifact_generated_at timestamptz not null,
  manifest_created_at timestamptz,
  planned_at timestamptz,
  sent_at timestamptz not null,
  offer_title text not null check (length(trim(offer_title)) > 0),
  offer_url text not null check (length(trim(offer_url)) > 0),
  offer_price numeric(12, 2),
  message_text text not null check (length(trim(message_text)) > 0),
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (profile, target, manifest_item_number, artifact_generated_at)
);

create index if not exists publication_events_profile_sent_at_idx
  on offers.publication_events (profile, sent_at desc);

create index if not exists publication_events_stable_key_sent_at_idx
  on offers.publication_events (stable_key, sent_at desc);

create index if not exists publication_events_target_sent_at_idx
  on offers.publication_events (target, sent_at desc);

drop trigger if exists publication_events_set_updated_at
  on offers.publication_events;

create trigger publication_events_set_updated_at
before update on offers.publication_events
for each row execute function offers.set_updated_at();

comment on table offers.publication_events is
  'Ledger auditavel de entregas confirmadas pelo worker no fluxo Cloud Run.';

comment on column offers.publication_events.publish_id is
  'Identificador imutavel da entrega confirmada usado para auditoria e conciliacao.';

comment on column offers.publication_events.payload is
  'Snapshot tecnico do artifact e dos metadados da confirmacao recebida pelo worker.';

alter table offers.publication_events enable row level security;

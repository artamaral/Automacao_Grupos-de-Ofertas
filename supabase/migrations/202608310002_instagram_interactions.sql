create table if not exists offers.instagram_comment_events (
  id uuid primary key default gen_random_uuid(),
  instagram_account_id text not null check (length(trim(instagram_account_id)) > 0),
  event_id text,
  comment_id text,
  media_id text,
  publication_event_id uuid references offers.publication_events(publish_id) on delete set null,
  item_id bigint,
  user_id text,
  username text,
  message_text text,
  event_at timestamptz,
  received_at timestamptz not null default now(),
  normalized_text text,
  keyword_matched boolean,
  matched_keyword text,
  public_reply_text text,
  public_reply_status text not null default 'not_attempted',
  public_reply_id text,
  private_reply_text text,
  private_reply_status text not null default 'not_attempted',
  private_reply_id text,
  processing_status text not null default 'received',
  failure_stage text,
  error_code text,
  error_detail text,
  processed_at timestamptz,
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists instagram_comment_events_comment_id_uidx
  on offers.instagram_comment_events (comment_id)
  where comment_id is not null;
create index if not exists instagram_comment_events_event_at_idx
  on offers.instagram_comment_events (event_at desc);
create index if not exists instagram_comment_events_user_event_at_idx
  on offers.instagram_comment_events (user_id, event_at desc);
create index if not exists instagram_comment_events_item_event_at_idx
  on offers.instagram_comment_events (item_id, event_at desc);
create index if not exists instagram_comment_events_media_event_at_idx
  on offers.instagram_comment_events (media_id, event_at desc);
create index if not exists instagram_comment_events_keyword_event_at_idx
  on offers.instagram_comment_events (matched_keyword, event_at desc);
create index if not exists instagram_comment_events_processing_event_at_idx
  on offers.instagram_comment_events (processing_status, event_at desc);

drop trigger if exists instagram_comment_events_set_updated_at on offers.instagram_comment_events;
create trigger instagram_comment_events_set_updated_at
before update on offers.instagram_comment_events
for each row execute function offers.set_updated_at();

alter table offers.instagram_comment_events enable row level security;

create table if not exists offers.instagram_dm_events (
  id uuid primary key default gen_random_uuid(),
  instagram_account_id text not null check (length(trim(instagram_account_id)) > 0),
  event_id text,
  message_id text,
  user_id text,
  recipient_id text,
  username text,
  message_text text,
  event_at timestamptz,
  received_at timestamptz not null default now(),
  cooldown_applied boolean not null default false,
  cooldown_reference_at timestamptz,
  reply_text text,
  reply_status text not null default 'not_attempted',
  reply_message_id text,
  reply_recipient_id text,
  processing_status text not null default 'received',
  failure_stage text,
  error_code text,
  error_detail text,
  processed_at timestamptz,
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists instagram_dm_events_message_id_uidx
  on offers.instagram_dm_events (message_id)
  where message_id is not null;
create index if not exists instagram_dm_events_event_at_idx
  on offers.instagram_dm_events (event_at desc);
create index if not exists instagram_dm_events_user_event_at_idx
  on offers.instagram_dm_events (user_id, event_at desc);
create index if not exists instagram_dm_events_user_reply_event_at_idx
  on offers.instagram_dm_events (user_id, reply_status, event_at desc);
create index if not exists instagram_dm_events_processing_event_at_idx
  on offers.instagram_dm_events (processing_status, event_at desc);

drop trigger if exists instagram_dm_events_set_updated_at on offers.instagram_dm_events;
create trigger instagram_dm_events_set_updated_at
before update on offers.instagram_dm_events
for each row execute function offers.set_updated_at();

alter table offers.instagram_dm_events enable row level security;

comment on table offers.instagram_comment_events is
  'Ledger permanente de comentarios Instagram e respectivas respostas publicas e privadas.';
comment on table offers.instagram_dm_events is
  'Ledger permanente de DMs Instagram e controle de cooldown de resposta automatica.';

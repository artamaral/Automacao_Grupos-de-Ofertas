create or replace function offers.reconcile_offer_publication_state(
  p_profile text,
  p_marketplace text,
  p_stable_key text
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_confirmation_count integer;
  v_last_sent_at timestamptz;
  v_selected_at timestamptz;
  v_item_id bigint;
  v_cooldown_until timestamptz;
begin
  if p_profile <> 'feminino' or p_marketplace <> 'shopee' then
    raise exception 'publication cooldown is only enabled for feminino/shopee';
  end if;

  select
    count(*)::integer,
    max(event.sent_at)
  into
    v_confirmation_count,
    v_last_sent_at
  from offers.publication_events event
  where event.profile = p_profile
    and event.marketplace = p_marketplace
    and event.stable_key = p_stable_key
    and event.delivery_status = 'confirmed'
    and event.sent_at is not null;

  if v_confirmation_count = 0 then
    update offers.offer_selection_state state
    set selected_at = null,
        cooldown_until = null,
        last_sent_at = null,
        selection_count = 0,
        selection_reason = case
          when state.similarity_status = 'suppressed' then state.selection_reason
          when state.selection_bucket in (
            'publication_cooldown_2d',
            'publication_cooldown_3d'
          ) then null
          else state.selection_reason
        end,
        selection_bucket = case
          when state.similarity_status = 'suppressed' then state.selection_bucket
          when state.selection_bucket in (
            'publication_cooldown_2d',
            'publication_cooldown_3d'
          ) then null
          else state.selection_bucket
        end,
        updated_at = now()
    where state.profile = p_profile
      and state.marketplace = p_marketplace
      and state.stable_key = p_stable_key;
    return;
  end if;

  select
    event.item_id,
    coalesce(event.planned_at, event.sent_at)
  into
    v_item_id,
    v_selected_at
  from offers.publication_events event
  where event.profile = p_profile
    and event.marketplace = p_marketplace
    and event.stable_key = p_stable_key
    and event.delivery_status = 'confirmed'
    and event.sent_at is not null
  order by event.sent_at desc, event.created_at desc, event.publish_id desc
  limit 1;

  v_cooldown_until := (
    ((v_last_sent_at at time zone 'America/Sao_Paulo')::date + 4)::timestamp
    at time zone 'America/Sao_Paulo'
  );

  insert into offers.offer_selection_state (
    profile,
    marketplace,
    stable_key,
    item_id,
    selected_at,
    cooldown_until,
    last_sent_at,
    selection_count,
    selection_reason,
    selection_bucket
  )
  values (
    p_profile,
    p_marketplace,
    p_stable_key,
    v_item_id,
    v_selected_at,
    v_cooldown_until,
    v_last_sent_at,
    v_confirmation_count,
    'publication_confirmed',
    'publication_cooldown_3d'
  )
  on conflict (profile, marketplace, stable_key)
  do update
  set item_id = coalesce(excluded.item_id, offer_selection_state.item_id),
      selected_at = excluded.selected_at,
      cooldown_until = excluded.cooldown_until,
      last_sent_at = excluded.last_sent_at,
      selection_count = excluded.selection_count,
      selection_reason = case
        when offer_selection_state.similarity_status = 'suppressed'
          then offer_selection_state.selection_reason
        else excluded.selection_reason
      end,
      selection_bucket = case
        when offer_selection_state.similarity_status = 'suppressed'
          then offer_selection_state.selection_bucket
        else excluded.selection_bucket
      end,
      updated_at = now();
end;
$$;

create or replace function offers.rebuild_offer_publication_state(
  p_profile text,
  p_marketplace text
)
returns bigint
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_stable_key text;
  v_reconciled bigint := 0;
begin
  if p_profile <> 'feminino' or p_marketplace <> 'shopee' then
    raise exception 'publication cooldown is only enabled for feminino/shopee';
  end if;

  for v_stable_key in
    select candidate.stable_key
    from (
      select event.stable_key
      from offers.publication_events event
      where event.profile = p_profile
        and event.marketplace = p_marketplace
        and event.delivery_status = 'confirmed'
        and event.sent_at is not null
      union
      select state.stable_key
      from offers.offer_selection_state state
      where state.profile = p_profile
        and state.marketplace = p_marketplace
        and (
          state.selection_bucket in (
            'publication_cooldown_2d',
            'publication_cooldown_3d'
          )
          or state.selected_at is not null
          or state.cooldown_until is not null
          or state.last_sent_at is not null
          or state.selection_count > 0
        )
    ) candidate
    order by candidate.stable_key
  loop
    perform offers.reconcile_offer_publication_state(
      p_profile,
      p_marketplace,
      v_stable_key
    );
    v_reconciled := v_reconciled + 1;
  end loop;

  return v_reconciled;
end;
$$;

comment on function offers.reconcile_offer_publication_state(text, text, text) is
  'Reconstroi o estado operacional de publicacao de um item a partir do ledger confirmado com cooldown de tres dias operacionais.';
comment on function offers.rebuild_offer_publication_state(text, text) is
  'Reconcilia em lote o cooldown de publicacao de tres dias operacionais; executar fora da janela diaria em andamento.';

# Ledger de publicacao no Supabase

Este documento descreve o historico auditavel de tentativas e resultados de
envio no MVP.

No MVP, o gravador principal pode ser o n8n. Workers Python ou Cloud Run podem
continuar existindo como referencia tecnica, mas nao sao requisito do fluxo
oficial.

## Status

Migration:

```text
supabase/migrations/202606290002_publication_events.sql
```

Tabela criada no schema `offers`:

- `publication_events`.

O objetivo desta tabela e responder:

- o que foi enviado ou tentado;
- quando ocorreu;
- para qual `target`;
- com qual `publish_id`;
- a partir de qual item da rodada.

## Papel operacional no MVP

O n8n registra a linha depois da tentativa de envio ou bloqueio operacional.

Status esperados:

- `confirmed`: envio confirmado pelo canal;
- `failed`: tentativa falhou;
- `cancelled`: envio bloqueado ou cancelado pela regra operacional.

O registro deve acontecer mesmo quando o destino for bloqueado pela allowlist,
desde que exista informacao suficiente para auditoria da rodada.

## Colunas principais

- `publish_id`: UUID imutavel da entrega.
- `profile`: perfil operacional, como `feminino`.
- `marketplace`: marketplace da oferta, como `shopee`.
- `stable_key`: identidade estavel da oferta.
- `item_id`: `item_id` do marketplace quando existir.
- `target`: destino logico usado pelo n8n.
- `channel_adapter`: canal usado, como `whatsapp`.
- `delivery_status`: `confirmed`, `failed` ou `cancelled`.
- `manifest_item_number`: numero sequencial da mensagem na rodada.
- `artifact_generated_at`: timestamp ou identificador temporal da rodada.
- `manifest_created_at`: timestamp de montagem da mensagem, quando existir.
- `planned_at`: horario planejado, quando existir.
- `sent_at`: horario confirmado ou tentado.
- `offer_title`, `offer_url`, `offer_price`: snapshot comercial.
- `message_text`: texto efetivamente enviado ou planejado.
- `payload`: metadados do n8n, `run_id`, erro do canal ou motivo de bloqueio.
- `created_at`, `updated_at`: auditoria da linha.

## Regra de idempotencia

Retries do n8n nao devem duplicar eventos da mesma mensagem.

A chave operacional e:

```text
(profile, target, manifest_item_number, artifact_generated_at)
```

Se a mesma confirmacao chegar novamente, o registro deve ser atualizado e o
`publish_id` deve permanecer o mesmo.

## Insert minimo pelo n8n

O workflow deve montar um payload equivalente a:

```sql
insert into offers.publication_events (
  profile,
  marketplace,
  stable_key,
  item_id,
  target,
  channel_adapter,
  delivery_status,
  manifest_item_number,
  artifact_generated_at,
  manifest_created_at,
  planned_at,
  sent_at,
  offer_title,
  offer_url,
  offer_price,
  message_text,
  payload
)
values (
  :profile,
  :marketplace,
  :stable_key,
  :item_id,
  :target,
  :channel_adapter,
  :delivery_status,
  :manifest_item_number,
  :artifact_generated_at,
  :manifest_created_at,
  :planned_at,
  :sent_at,
  :offer_title,
  :offer_url,
  :offer_price,
  :message_text,
  :payload
)
on conflict (profile, target, manifest_item_number, artifact_generated_at)
do update
set delivery_status = excluded.delivery_status,
    sent_at = excluded.sent_at,
    message_text = excluded.message_text,
    payload = excluded.payload,
    updated_at = now()
returning publish_id;
```

## Consultas uteis

Ultimas publicacoes por profile:

```sql
select
  publish_id,
  profile,
  target,
  sent_at,
  delivery_status,
  offer_title,
  offer_url
from offers.publication_events
where profile = 'feminino'
order by sent_at desc
limit 50;
```

Historico por oferta:

```sql
select
  publish_id,
  profile,
  target,
  sent_at,
  delivery_status
from offers.publication_events
where stable_key = '<stable_key>'
order by sent_at desc;
```

Conciliacao por rodada:

```sql
select
  artifact_generated_at,
  profile,
  count(*) as total_events
from offers.publication_events
group by 1, 2
order by artifact_generated_at desc, profile;
```

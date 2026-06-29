# Ledger de publicacao no Supabase

Este documento descreve o historico auditavel de publicacoes confirmadas pelo
worker no fluxo `Cloud Run`.

## Status

Migration:

```text
supabase/migrations/202606290002_publication_events.sql
```

Tabela criada no schema `offers`:

- `publication_events`.

O objetivo desta tabela e responder de forma direta:

- o que foi publicado;
- quando foi publicado;
- para qual target;
- com qual `publish_id`;
- a partir de qual item do artifact.

## Papel operacional

O worker registra a publicacao no momento em que recebe a confirmacao de
entrega via:

```text
POST /confirm-delivery
POST /confirm-window-deliveries
```

O caminho de escrita fica em `src/ofertas_bot/cloud_runner.py`.

O contrato de persistencia fica em
`src/ofertas_bot/storage/supabase_publication_event_store.py`.

Sem `SUPABASE_DB_URL`, o worker continua atualizando `selection_state.json`, mas
nao grava `publication_events`. Em ambiente oficial do worker, essa variavel
deve estar configurada.

## Colunas principais

- `publish_id`: UUID imutavel da entrega confirmada.
- `profile`: perfil operacional, como `feminino`.
- `marketplace`: marketplace da oferta, como `shopee`.
- `stable_key`: identidade estavel da oferta.
- `item_id`: `item_id` do marketplace quando existir.
- `target`: destino logico confirmado pelo worker.
- `channel_adapter`: adaptador do canal presente no artifact.
- `delivery_status`: status operacional da entrega.
- `manifest_item_number`: identificador da mensagem dentro do artifact.
- `artifact_generated_at`: timestamp da rodada que originou a entrega.
- `manifest_created_at`: timestamp do manifesto para aquela mensagem.
- `planned_at`: horario planejado no artifact.
- `sent_at`: horario confirmado como enviado.
- `offer_title`, `offer_url`, `offer_price`: snapshot comercial da oferta.
- `message_text`: texto efetivamente confirmado.
- `payload`: metadados tecnicos do worker e do artifact.
- `created_at`, `updated_at`: auditoria da linha.

## Regra de idempotencia

O worker pode receber retry de confirmacao. Para nao duplicar eventos da mesma
mensagem, a tabela usa a chave unica:

```text
(profile, target, manifest_item_number, artifact_generated_at)
```

Se a mesma confirmacao chegar novamente, o registro e atualizado e o
`publish_id` permanece o mesmo.

## Consultas uteis

Ultimas publicacoes por profile:

```sql
select
  publish_id,
  profile,
  target,
  sent_at,
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

Conciliacao por artifact:

```sql
select
  artifact_generated_at,
  profile,
  count(*) as total_confirmed
from offers.publication_events
group by 1, 2
order by artifact_generated_at desc, profile;
```

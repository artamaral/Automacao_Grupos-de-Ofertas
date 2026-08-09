# Ledger de publicacao no Supabase

Este documento descreve o historico auditavel de tentativas e resultados de
envio no MVP.

No MVP, o gravador principal pode ser o n8n. Workers Python ou Cloud Run podem
continuar existindo como referencia tecnica, mas nao sao requisito do fluxo
oficial.

## Status

Migration base:

```text
supabase/migrations/202606290002_publication_events.sql
```

Migration complementar aplicada para dry-run sem envio real:

```text
supabase/migrations/202608090001_allow_null_sent_at_publication_events.sql
```

Timezone operacional do database:

```text
supabase/migrations/202608090002_set_database_timezone_sao_paulo.sql
```

O database `postgres` usa `America/Sao_Paulo` como timezone padrao para novas
sessoes. Os timestamps permanecem em colunas `timestamptz`; nao ha conversao de
dados historicos.

Tabela criada no schema `offers`:

- `publication_events`.

O objetivo desta tabela e responder:

- o que foi enviado ou tentado;
- quando ocorreu;
- para qual `target`;
- com qual `publish_id`;
- a partir de qual item da rodada;
- quais ofertas ja foram confirmadas e nao devem ser repostadas para o mesmo
  destino/canal no MVP.

## Papel operacional no MVP

O n8n registra a linha depois da tentativa de envio ou bloqueio operacional.

Status esperados:

- `confirmed`: envio confirmado pelo canal, ou etapa logica de pronto para canal
  real enquanto o node de envio ainda nao foi acoplado;
- `failed`: tentativa falhou;
- `cancelled`: envio bloqueado, cancelado pela regra operacional ou dry-run sem
  envio real.

O registro deve acontecer mesmo quando o destino for bloqueado pela allowlist,
desde que exista informacao suficiente para auditoria da rodada.

## Papel na selecao anti-repost

A query MVP do n8n usa `publication_events` para nao selecionar novamente uma
oferta ja confirmada para o mesmo `target` e `channel_adapter`.

A regra e intencionalmente conservadora:

- `delivery_status = 'confirmed'` bloqueia nova selecao do mesmo `stable_key`
  para o mesmo profile, marketplace, target e canal;
- `delivery_status = 'cancelled'` nao bloqueia nova selecao, porque cobre
  dry-runs e bloqueios de allowlist;
- a idempotencia de uma mesma rodada continua separada e usa
  `(profile, target, manifest_item_number, artifact_generated_at)`.

Filtro esperado na query de ranking:

```sql
and not exists (
  select 1
  from offers.publication_events event
  where event.profile = ranking.profile
    and event.marketplace = ranking.marketplace
    and event.stable_key = ranking.stable_key
    and event.target = :target
    and event.channel_adapter = :channel_adapter
    and event.delivery_status = 'confirmed'
)
```

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
- `sent_at`: horario confirmado/tentado; fica `null` em dry-run sem envio real.
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
order by sent_at desc nulls last
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
order by sent_at desc nulls last;
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

Ofertas confirmadas que bloqueiam repost para um destino/canal:

```sql
select
  profile,
  marketplace,
  target,
  channel_adapter,
  stable_key,
  max(sent_at) as last_confirmed_at,
  count(*) as confirmations
from offers.publication_events
where delivery_status = 'confirmed'
  and target = 'teste-whatsapp'
  and channel_adapter = 'whatsapp'
group by 1, 2, 3, 4, 5
order by last_confirmed_at desc nulls last;
```

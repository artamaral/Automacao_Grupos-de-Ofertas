# Retomada: n8n MVP dry-run

Data da retomada: 2026-08-09.

## Estado atual

- VPS operacional em `/opt/automacao_grupo_compras/n8n`.
- n8n self-hosted 2.32.6 rodando em Docker Compose com Postgres local e
  `n8nio/runners`.
- URL publica do painel: `https://n8n-owco.srv1805131.hstgr.cloud/`.
- `N8N_WEBHOOK_URL` configurado no `.env` e no Compose operacional.
- Workflow `ofertas-mvp-supabase` importado no painel do n8n e mantido inativo.
- Credencial Postgres real do Supabase criada no painel do n8n.
- Primeiro dry-run manual executado com sucesso e registrado no Supabase.
- `sent_at` foi ajustado para ficar `null` em dry-run.
- A coluna `offers.publication_events.sent_at` permite `null` via migration
  `supabase/migrations/202608090001_allow_null_sent_at_publication_events.sql`.
- Idempotencia do registro em `offers.publication_events` validada sem
  duplicatas para a chave operacional.
- Teste logico com `dry_run=false` registrou `delivery_status = confirmed`,
  `send_result = ready_for_real_channel_node` e `sent_at` preenchido.
- A selecao anti-repost foi validada: ofertas ja confirmadas para o mesmo
  `target` e `channel_adapter` deixam de ser selecionadas novamente.
- Timezone padrao do database Supabase ajustado para `America/Sao_Paulo` via
  migration `supabase/migrations/202608090002_set_database_timezone_sao_paulo.sql`.
- Adapter WhatsApp definido para uso agora: WAHA self-hosted, conforme
  [`docs/decisao-waha-whatsapp-n8n.md`](decisao-waha-whatsapp-n8n.md).

## Credencial Supabase no n8n

O workflow usa nodes `Postgres`, entao a credencial correta e uma credencial
Postgres apontando para o banco do Supabase.

Nao usar para esse workflow:

- publishable key;
- anon key;
- service role key;
- OAuth;
- API key.

Na validacao, a conexao so passou com:

- SSL em `require`;
- `Ignore SSL Issues (Insecure)` habilitado.

Isso mantem transporte criptografado, mas ignora a validacao completa da cadeia
TLS. Deve ser tratado como pendencia de hardening.

## Correcoes manuais feitas no painel do n8n

Durante o teste, dois nodes `Set` importados produziram output vazio (`[{}]`):

1. `Set Contexto MVP`;
2. `Simular Envio MVP`.

Contorno aplicado: substituir por nodes `Code` no painel do n8n. O JSON
versionado tambem foi atualizado para manter esses dois nodes como `Code`.

### Nome correto dos nodes

Inicio do fluxo:

```text
Trigger Manual
→ Set Contexto MVP
→ Validar Contexto
→ Consultar Ranking Supabase
```

Final do fluxo:

```text
Validar Allowlist
→ Simular Envio MVP
→ Montar Upsert Publication Event
→ Registrar Resultado Supabase
```

### Codigo usado em `Set Contexto MVP`

```javascript
const input = items[0]?.json || {};

return [
  {
    json: {
      ...input,
      dry_run: input.dry_run === undefined ? true : input.dry_run,
      limit: Number(input.limit || 1),
      profile: input.profile || 'feminino',
      marketplace: input.marketplace || 'shopee',
      target: input.target || 'teste-whatsapp',
      allowed_targets_csv: input.allowed_targets_csv || 'teste-whatsapp',
      channel_adapter: input.channel_adapter || 'whatsapp',
      run_id: input.run_id || new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '-mvp-supabase',
    },
  },
];
```

### Codigo usado em `Simular Envio MVP`

```javascript
const item = $json;

return {
  json: {
    ...item,
    send_result:
      item.target_allowed && !item.dry_run
        ? 'ready_for_real_channel_node'
        : item.target_allowed
          ? 'dry_run_not_sent'
          : 'blocked_by_allowlist',
    sent_at: item.dry_run ? null : new Date().toISOString(),
  },
};
```

## Regra anti-repost

O problema observado foi que execucoes sucessivas selecionavam sempre o mesmo
item, porque a query consumia o topo de `offers.v_offer_ranking_current` sem
considerar o historico de publicacao.

A regra validada no painel foi excluir da query de ranking ofertas ja
confirmadas em `offers.publication_events` para o mesmo destino e canal:

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

Essa regra usa `delivery_status = 'confirmed'` como bloqueio anti-repost. Linhas
`cancelled`, incluindo dry-run, nao bloqueiam nova selecao.

## Evidencia do dry-run inicial

Contexto validado:

```json
{
  "dry_run": true,
  "limit": 1,
  "profile": "feminino",
  "marketplace": "shopee",
  "target": "teste-whatsapp",
  "allowed_targets_csv": "teste-whatsapp",
  "channel_adapter": "whatsapp"
}
```

Registro criado em `offers.publication_events`:

```text
publish_id: 461e54bf-aff6-4907-870d-3eedc15d047d
profile: feminino
marketplace: shopee
target: teste-whatsapp
channel_adapter: whatsapp
delivery_status: cancelled
payload.dry_run: true
payload.send_result: dry_run_not_sent
payload.target_allowed: true
payload.blocked_reason: null
```

Oferta usada no dry-run inicial:

```text
item_id: 58211202356
offer_title: Bolsa Feminina Clutch De Ombro Pequena Sofisticada Alça Regulável
offer_url: https://s.shopee.com.br/4LHIXyhV9L
offer_price: 16.99
rank_profile: 1
rank_subniche: 1
```

Mensagem gerada:

```text
Bolsa Feminina Clutch De Ombro Pequena Sofisticada Alça Regulável

Preco: R$ 16,99
Avaliacao: 4.80

Link: https://s.shopee.com.br/4LHIXyhV9L

Aviso: este link pode gerar comissao de afiliado. Preco e disponibilidade podem mudar.
```

## Pendencias antes de ativar o workflow

1. Endurecer TLS da credencial Postgres do Supabase, se viavel.
2. Acoplar o node real WAHA protegido por `dry_run=false` e allowlist,
   registrando erro/status do adapter no payload.
3. Fazer teste real minimo apenas com destino controlado e allowlist.
4. Ativar o workflow somente depois do teste real minimo passar.

## Comandos uteis

Estado dos containers:

```bash
cd /opt/automacao_grupo_compras/n8n
docker compose --env-file .env -f docker-compose.yml ps
```

Logs:

```bash
cd /opt/automacao_grupo_compras/n8n
docker compose --env-file .env -f docker-compose.yml logs --tail=200 n8n n8n-runner postgres
```

Healthcheck interno:

```bash
cd /opt/automacao_grupo_compras/n8n
docker compose --env-file .env -f docker-compose.yml exec -T n8n wget -qO- http://127.0.0.1:5678/healthz
```

Query de verificacao no Supabase:

```sql
select
  publish_id,
  profile,
  marketplace,
  target,
  channel_adapter,
  delivery_status,
  offer_title,
  offer_url,
  payload,
  created_at,
  updated_at
from offers.publication_events
where publish_id = '461e54bf-aff6-4907-870d-3eedc15d047d';
```

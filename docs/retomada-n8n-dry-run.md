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
- WAHA implantado na VPS em 2026-08-09 como servico `waha` no Compose
  operacional, usando `devlikeapro/waha`, porta local `127.0.0.1:3000`, volume
  persistente `data/waha/.sessions` e API protegida por `X-Api-Key`.
- Credenciais operacionais do WAHA ficam somente em
  `/opt/automacao_grupo_compras/n8n/waha-operator.txt` com modo `0600`.
- Sessao WAHA `default` criada, pareada e conectada; estado esperado:
  `WORKING` / `CONNECTED`.
- Envio manual controlado pelo WAHA validado em 2026-08-09 para destino de
  teste allowlisted, com resposta HTTP 201.
- Workflow real do n8n acoplado ao WAHA com os nodes `Preparar Envio WAHA`,
  `IF Pode Enviar WAHA`, `Enviar WhatsApp WAHA` e
  `Normalizar Resultado WAHA`.
- Credencial `WAHA Header Auth` criada no n8n como `httpHeaderAuth`, usando
  `X-Api-Key`. O valor da chave permanece somente fora do Git.
- Teste real controlado pelo workflow n8n executado em 2026-08-09 com
  `dry_run=false`, `limit=1` e destino explicitamente allowlisted. Execucao n8n
  `23` finalizou com `success`, WAHA respondeu HTTP 201, o payload normalizado
  registrou `send_result = sent_to_adapter` e Supabase retornou
  `publish_id = 1e99a91a-9684-4e69-9024-f0c4ae0ea0f3`.
- Apos o teste, o `pinData` do workflow foi restaurado para `dry_run=true` e
  `target=teste-whatsapp`.
- Apos revisar a documentacao de copy, o node `Montar Mensagens` foi alinhado
  ao template Shopee oficial de `config/message_templates/shopee.txt`, usando
  cupom global, preco em BRL, desconto calculado por `reference_price` e
  marcador `(anúncio)`.
- O workflow foi ajustado para incluir `image_url` na query de ranking e enviar
  a oferta pelo WAHA como imagem com legenda via `POST /api/sendImage`.
- Envios reais agora exigem `image_url` valida. Quando ausente, o node
  `Preparar Envio WAHA` registra `adapter_missing_image_url` e nao chama o
  adapter.

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

Final do fluxo com WAHA:

```text
Validar Allowlist
→ Simular Envio MVP
→ Preparar Envio WAHA
→ IF Pode Enviar WAHA
  → true: Enviar WhatsApp WAHA → Normalizar Resultado WAHA
  → false: Montar Upsert Publication Event
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

Mensagem gerada no dry-run inicial, antes do alinhamento ao template Shopee
oficial:

```text
Bolsa Feminina Clutch De Ombro Pequena Sofisticada Alça Regulável

Preco: R$ 16,99
Avaliacao: 4.80

Link: https://s.shopee.com.br/4LHIXyhV9L

Aviso: este link pode gerar comissao de afiliado. Preco e disponibilidade podem mudar.
```

Padrao atual para novos envios Shopee:

```text
🔥 {{facts.title}}

🏪 Loja: {{facts.marketplace}}

💵 {{facts.price | brl}}

🏷️ {{facts.discount_percent | round}}% OFF

⭐ Avaliação: {{facts.rating | rating_br}}/5

🎟️ Resgate o cupom desta página:
{{coupon_url}}

✅ Link do produto:
{{facts.url}}

(anúncio)
```

## Pendencias antes de ativar o workflow

1. Endurecer TLS da credencial Postgres do Supabase, se viavel.
2. Ativar o workflow somente depois de revisar janela/volume inicial de
   operacao.

## Teste real controlado pelo n8n

Antes de executar, confirmar no painel:

- workflow `ofertas-mvp-supabase` ainda inativo;
- node `Enviar WhatsApp WAHA` usando URL `http://waha:3000/api/sendImage`;
- credencial `WAHA Header Auth` selecionada;
- sessao WAHA `default` em `WORKING` / `CONNECTED`;
- destino de teste presente em `target` e em `allowed_targets_csv`.

Antes de abrir/executar o workflow no painel, fechar abas antigas do editor n8n
e reaplicar o JSON versionado com o guard:

```bash
python3 scripts/n8n/deploy_workflow_guard.py --mode grupo-real
```

O guard atualiza o workflow `OfertasMvpSupab1` a partir do Git, mantem
`active=false`, exige `POST /api/sendImage`, bloqueia `POST /api/sendText`,
confirma o template Shopee oficial e deixa o `pinData` pronto para envio manual
do grupo real com `dry_run=false` e `limit=1`.

Para validar sem alterar o n8n:

```bash
python3 scripts/n8n/deploy_workflow_guard.py --dry-run --mode grupo-real
```

Checklist curto por rodada operacional:

```bash
python3 scripts/n8n/run_operational_round.py --mode teste-telefone
```

O wrapper executa `deploy_workflow_guard.py --mode <mode>`,
`run_workflow_manual.py --mode <mode>` e `check_last_execution.py`, parando no
primeiro erro. Nos modos `grupo-real` e `teste-telefone`, ele chama a checagem
com `--expect-real-image`; no modo `dry-run`, nao exige
`adapter_response_type=image`.

Resumo final esperado no terminal:

```text
execution_id=<id>
endpoint=sendImage
publish_id=<uuid>
delivery_status=confirmed
adapter_response_type=image
copy_template=novo
```

Para depurar passo a passo:

```bash
python3 scripts/n8n/deploy_workflow_guard.py --mode grupo-real
python3 scripts/n8n/run_workflow_manual.py --mode grupo-real
python3 scripts/n8n/check_last_execution.py --expect-real-image
```

Modos disponiveis:

- `grupo-real`: grupo `grupo-ofertas-feminino`;
- `teste-telefone`: telefone `5511975235421`;
- `dry-run`: sem envio real.

`preserve-pindata` existe somente no `deploy_workflow_guard.py`, para reaplicar
o workflow sem alterar `pinData`.

O `run_workflow_manual.py` exige `--mode` explicitamente para evitar envio real
acidental. A checagem final deve mostrar `endpoint=sendImage`,
`adapter_response_type=image`, `delivery_status=confirmed` e
`copy_template=novo`.

Payload recomendado para a execucao manual controlada:

```json
{
  "dry_run": false,
  "limit": 1,
  "profile": "feminino",
  "marketplace": "shopee",
  "target": "55DDDNUMERO",
  "allowed_targets_csv": "55DDDNUMERO",
  "channel_adapter": "whatsapp"
}
```

Resultado esperado:

- node `Enviar WhatsApp WAHA` retorna HTTP 201 ou corpo com id de mensagem;
- node `Normalizar Resultado WAHA` define `send_result = sent_to_adapter`;
- `offers.publication_events.delivery_status = confirmed`;
- `payload.adapter_status = sent_to_adapter`;
- `payload.adapter_message_id` preenchido quando a WAHA retornar id;
- `payload.image_url` e `payload.waha_image_url` preenchidos;
- uma nova execucao para o mesmo `target` nao deve reenviar a mesma oferta ja
  confirmada.

Resultado atual validado em 2026-08-09:

- branch operacional: `feat/supabase-cloud-run`;
- validacao local: `ruff check .` passou e `pytest` retornou `451 passed`;
- wrapper usado: `scripts/n8n/run_operational_round.py`;
- `dry-run`: execucao `44`, `delivery_status=cancelled`,
  `send_result=dry_run_not_sent`, `copy_template=novo`;
- `teste-telefone`: execucao `45`, `endpoint=sendImage`,
  `delivery_status=confirmed`, `adapter_response_type=image`,
  `copy_template=novo`;
- `grupo-real`: execucao `46`, `endpoint=sendImage`,
  `publish_id=029c13e7-8236-4a73-8beb-cbb797b2a576`,
  `delivery_status=confirmed`, `adapter_response_type=image`,
  `copy_template=novo`;
- envio real para `grupo-ofertas-feminino` aceito pela WAHA como imagem com
  legenda;
- workflow mantido `active=false`, com operacao manual/controlada via API do
  n8n.

Schedule automatico preparado em 2026-08-09:

- node `Schedule Grupo Real` versionado junto ao `Trigger Manual`;
- cron: `0 8-21 * * *`;
- timezone: `America/Sao_Paulo`;
- frequencia: 1 execucao por hora, das 08:00 as 21:00;
- contexto fixo em `Set Contexto Schedule Grupo`;
- destino: `grupo-ofertas-feminino`;
- chat WAHA: `120363412864266334@g.us`;
- `dry_run=false`, `limit=1`, `allowed_targets_csv=grupo-ofertas-feminino`;
- envio esperado: `POST /api/sendImage`;
- `deploy_workflow_guard.py` valida o schedule e mantem `active=false`;
- workflow aplicado no n8n com `versionCounter=40` e `active=false`;
- ativacao e pausa continuam sendo feitas manualmente no painel do n8n;
- proxima acao para iniciar o teste automatico: ativar o workflow no painel.

Resultado historico validado em 2026-08-09:

- execucao n8n: `23`;
- status da execucao: `success`;
- WAHA: `POST /api/sendText` com HTTP 201;
- `send_result`: `sent_to_adapter`;
- `adapter_status`: `sent_to_adapter`;
- `delivery_status`: `confirmed`;
- `publish_id`: `1e99a91a-9684-4e69-9024-f0c4ae0ea0f3`;
- oferta enviada: `58211202356`;
- `pinData` restaurado para `dry_run=true` depois do teste.

Observacao: essa execucao validou o canal WAHA com o template minimo anterior.
O workflow versionado foi ajustado depois para usar o template Shopee oficial
nos proximos testes/envios. Depois disso, o workflow tambem foi ajustado para
enviar imagem com legenda usando `image_url` e `POST /api/sendImage`.

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
docker compose --env-file .env -f docker-compose.yml logs --tail=200 waha
```

Healthcheck interno:

```bash
cd /opt/automacao_grupo_compras/n8n
docker compose --env-file .env -f docker-compose.yml exec -T n8n wget -qO- http://127.0.0.1:5678/healthz
docker compose --env-file .env -f docker-compose.yml exec -T n8n wget -qO- http://waha:3000/health
```

Tunel local para dashboard WAHA:

```bash
ssh -N -L 3000:127.0.0.1:3000 <usuario>@<host-da-vps>
```

Abrir:

```text
http://127.0.0.1:3000/dashboard
```

Antes do dashboard, validar o tunel no navegador local:

```text
http://127.0.0.1:3000/health
```

Retorno esperado: JSON com `status: ok`.

No dashboard, configurar a conexao do servidor como:

```text
WAHA VPS URL: http://127.0.0.1:3000
```

Nao usar `/dashboard` nesse campo.

As credenciais estao em:

```text
/opt/automacao_grupo_compras/n8n/waha-operator.txt
```

Usar usuario/senha para abrir a interface. Para o dashboard carregar sessoes,
chats e grupos, usar a linha `X-Api-Key:` como API key da conexao. A senha do
dashboard nao substitui a `X-Api-Key`.

Se aparecer `Server connection failed` com `/health` respondendo `status: ok`,
o WAHA esta acessivel pelo navegador e a causa provavel e URL de conexao errada
ou API key ausente/incorreta no dashboard.

Para envio manual em grupo WhatsApp, usar `target` como nome logico auditavel e
`target_chat_id` como chat id real do WAHA, normalmente terminado em `@g.us`.
Exemplo de entrada manual:

```json
{
  "dry_run": false,
  "limit": 1,
  "profile": "feminino",
  "marketplace": "shopee",
  "target": "grupo-ofertas-feminino",
  "target_chat_id": "120363XXXXXXXXXXXX@g.us",
  "allowed_targets_csv": "grupo-ofertas-feminino",
  "channel_adapter": "whatsapp"
}
```

O `target` deve estar em `allowed_targets_csv`. O `target_chat_id` substitui o
destino somente na chamada da WAHA. Apos o teste, restaurar `dry_run=true` e o
destino de teste.

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

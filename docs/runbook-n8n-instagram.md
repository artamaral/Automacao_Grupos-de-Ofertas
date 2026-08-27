# Runbook n8n Instagram Shopee

Este runbook descreve a operacao controlada do fluxo Instagram Shopee. O
WhatsApp continua em workflow separado e nao deve ser alterado por esta rotina.

## Contrato

Fluxo operacional:

```text
offers.daily_dispatch_plan / offers.v_daily_dispatch_ready
  -> resolvedor Python em lote
  -> offers.offer_media_assets
  -> offers.v_instagram_dispatch_ready
  -> workflow n8n Instagram
  -> Instagram Graph API
  -> offers.publication_events
```

Responsabilidades:

- Python resolve HTML Shopee e persiste apenas URLs/metadados;
- Supabase permanece como fonte operacional;
- n8n consome somente itens prontos;
- n8n revalida URLs antes de criar container;
- n8n registra confirmacao ou falha em `offers.publication_events`;
- n8n nao raspa HTML, nao recalcula ranking e nao baixa midia.

## Preparacao da midia

Dry-run local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.resolve_instagram_media_batch `
  --profile feminino `
  --marketplace shopee `
  --date 2026-08-15 `
  --limit 3 `
  --dry-run `
  --only-missing
```

Escrita real, somente apos revisar o resumo do dry-run:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.resolve_instagram_media_batch `
  --profile feminino `
  --marketplace shopee `
  --date 2026-08-15 `
  --limit 20 `
  --apply `
  --only-missing
```

Saida esperada:

```text
dry_run=true
processed=3
valid=3
with_video=3
image_only=0
no_media=0
failed=0
total_images=<n>
```

## View de consumo

O workflow deve consultar `offers.v_instagram_dispatch_ready`.

No contrato atual, `planned_hour` continua exposto apenas como auditoria herdada
do planner diario. O horario efetivo da publicacao Instagram e definido pelo
schedule do n8n ou pela execucao manual.

A superficie Instagram nao depende mais de
`offers.v_daily_dispatch_ready.is_ready_for_dispatch`. Ela usa:

- `offers.daily_dispatch_plan` com `dispatch_status='planned'`;
- `offers.offer_media_assets` com `status='valid'`;
- `offers.v_offer_ranking_current` apenas para enriquecer copy e observabilidade
  (`refresh_status`, `is_eligible`, `ineligibility_reasons`).

Reels:

```sql
select *
from offers.v_instagram_dispatch_ready
where profile = 'feminino'
  and marketplace = 'shopee'
  and instagram_format = 'reels'
order by planned_date, daily_sequence, instagram_format desc
limit 1;
```

Carrossel:

```sql
select *
from offers.v_instagram_dispatch_ready
where profile = 'feminino'
  and marketplace = 'shopee'
  and instagram_format = 'carousel'
order by planned_date, daily_sequence, instagram_format desc
limit 1;
```

O claim concorrente deve travar a linha de `offers.daily_dispatch_plan` com
`FOR UPDATE SKIP LOCKED`; a view so define a superficie pronta e a ordenacao.
O workflow Instagram nao deve depender da hora materializada na fila para
decidir quando publicar.

## Workflow

Artefatos versionados:

```text
n8n/workflows/ofertas-instagram-supabase.json
n8n/payloads/ofertas-instagram-supabase-context.example.json
scripts/n8n/deploy_instagram_workflow_guard.py
```

Validacao local segura:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_n8n_instagram_deploy_workflow_guard.py
python scripts/n8n/deploy_instagram_workflow_guard.py --dry-run --mode safe
```

Deploy controlado na VPS:

```powershell
python scripts/n8n/deploy_instagram_workflow_guard.py --mode safe
```

O guard mantem `active=false`. A ativacao automatica nao faz parte do MVP.
Quando o workflow for ativado, o cron do n8n passa a ser a fonte de horario;
o Supabase entrega apenas o proximo item pronto e ordenado.

## Credenciais Instagram na VPS

O ambiente operacional ainda guarda os valores brutos no `.env` da VPS, sem
versionar, mas o workflow publicado deve usar credencial `httpHeaderAuth` do
n8n para evitar `access to env vars denied` nos nodes HTTP:

```env
INSTAGRAM_ACCESS_TOKEN=<token>
INSTAGRAM_BUSINESS_ACCOUNT_ID=<id>
INSTAGRAM_WHATSAPP_GROUP_URL=https://chat.whatsapp.com/FWM9EbDd0eQ7bHxr2iOf9K
```

Depois de atualizar o `.env`, reiniciar o stack do n8n:

```bash
cd /opt/automacao_grupo_compras/n8n
docker compose --env-file .env -f docker-compose.yml up -d
```

Validacao sem imprimir segredo:

```bash
grep -q '^INSTAGRAM_ACCESS_TOKEN=' /opt/automacao_grupo_compras/n8n/.env \
  && echo INSTAGRAM_ACCESS_TOKEN=present
grep -q '^INSTAGRAM_BUSINESS_ACCOUNT_ID=' /opt/automacao_grupo_compras/n8n/.env \
  && echo INSTAGRAM_BUSINESS_ACCOUNT_ID=present
grep -q '^INSTAGRAM_WHATSAPP_GROUP_URL=' /opt/automacao_grupo_compras/n8n/.env \
  && echo INSTAGRAM_WHATSAPP_GROUP_URL=present
```

Criar ou recriar a credencial HTTP do Instagram a partir do token ja presente
no `.env`, sem expor o valor:

```bash
cd /opt/automacao_grupo_compras/app
python3 scripts/n8n/configure_instagram_http_credential_vps.py --apply --host <ssh-host> --confirm-remote-write CREATE_INSTAGRAM_HTTP_CREDENTIAL
```

Se algum node como `Criar Filhos Carrossel` continuar acusando
`access to env vars denied`, inspecione a credencial antes de testar de novo:

```bash
cd /opt/automacao_grupo_compras/app
python3 scripts/n8n/configure_instagram_http_credential_vps.py --inspect --host <ssh-host>
```

Esperado no `--inspect`:

- `value_has_bearer_prefix=true`
- `value_uses_expression=false`
- `value_uses_env=false`
- `workflow_has_process_env=false`
- `workflow_has_env_expression=false`

## Teste real controlado

Pre-condicoes:

- migrations de midia aplicadas no Supabase;
- pelo menos 1 item com `video_url` valido;
- pelo menos 1 item com `image_urls` valido;
- workflow Instagram importado e `active=false`;
- target `oferta.femininas` presente na allowlist/config;
- credenciais da Instagram Graph API configuradas no ambiente operacional, fora
  do Git;
- `INSTAGRAM_WHATSAPP_GROUP_URL` configurado no ambiente operacional para a
  copy final do Instagram. Link publico atual:
  `https://chat.whatsapp.com/FWM9EbDd0eQ7bHxr2iOf9K`.
- O link deve ficar cadastrado tambem no perfil do Instagram. Links em legenda
  de Reels/feed aparecem como texto, nao como URL clicavel.

Execucao controlada:

```powershell
python scripts/n8n/deploy_instagram_workflow_guard.py --mode instagram-real-test
python scripts/n8n/run_workflow_manual.py --mode instagram-real-test
python scripts/n8n/check_last_execution.py --workflow-id OfertasInstagramSupab1
```

Se os scripts de execucao manual ainda estiverem acoplados ao WhatsApp, criar
equivalentes Instagram antes do teste real.

## Registro em `publication_events`

Usar:

```text
channel_adapter = instagram_reels
channel_adapter = instagram_carousel
```

`delivery_status` continua limitado a:

```text
confirmed
failed
cancelled
```

Estados intermediarios ficam em `payload`, incluindo:

- `dry_run`;
- `instagram_format`;
- `media_validation`;
- `blocked_reason`;
- `container_status`;
- `container_id`;
- resposta resumida da API sem tokens.

Container criado nao e prova de publicacao. `confirmed` so deve ser gravado
apos `media_publish` confirmado.

## Falhas de midia

Se a revalidacao falhar antes da publicacao:

- atualizar `offers.offer_media_assets.status` para `stale`;
- preencher `last_checked_at` e `error_detail`;
- registrar `publication_events.delivery_status='failed'`;
- usar `payload.blocked_reason='media_revalidation_failed'`;
- nao tentar publicar o item.

## Limites do MVP

- ate 3 Reels por dia; as janelas efetivas ficam no schedule do n8n, nao na
  view do Supabase;
- nichos preferenciais: `maquiagem-geral`, `skincare-facial` e
  `acessorios-femininos`;
- 1 carrossel diario para moda quando houver midia valida;
- fallback sempre pela ordem materializada em `offers.daily_dispatch_plan`;
- sem publicacao automatica em massa;
- sem download, transcodificacao ou hospedagem propria de midia.

## 2026-08-27 - Publicacao do workflow de producao

Etapa concluida:

- a validacao de producao do guard passou para `OfertasInstagramSupab1`;
- a versao `f0385f9d-19ea-4809-ab59-080f54d61a3c` foi implantada em modo
  `instagram-production`, com cron `0 10,12,14,16,18,20 * * *`;
- a versao atual foi publicada pelo comando oficial
  `n8n publish:workflow --id=OfertasInstagramSupab1`;
- o n8n listou `OfertasInstagramSupab1` entre os workflows ativos;
- a validacao manual anterior registrou tres eventos `confirmed` de
  `instagram_reels` e tres de `instagram_carousel` em 2026-08-27.

Pendencia operacional explicita:

- o CLI do n8n informou que a publicacao so passa a valer no processo em
  execucao apos reiniciar o servico `n8n`. Esse reinicio ainda nao foi feito,
  pois interrompe brevemente execucoes dos workflows hospedados no mesmo
  servico. Portanto, o workflow esta publicado/ativo no banco, mas o cron de
  producao ainda nao deve ser considerado efetivo ate essa manutencao.

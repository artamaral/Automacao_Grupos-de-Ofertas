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

Reels:

```sql
select *
from offers.v_instagram_dispatch_ready
where profile = 'feminino'
  and marketplace = 'shopee'
  and instagram_format = 'reels'
order by planned_date, planned_hour, slot_sequence, daily_sequence
limit 1;
```

Carrossel:

```sql
select *
from offers.v_instagram_dispatch_ready
where profile = 'feminino'
  and marketplace = 'shopee'
  and instagram_format = 'carousel'
order by planned_date, planned_hour, slot_sequence, daily_sequence
limit 1;
```

O claim concorrente deve travar a linha de `offers.daily_dispatch_plan` com
`FOR UPDATE SKIP LOCKED`; a view so define a superficie pronta.

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

## Teste real controlado

Pre-condicoes:

- migrations de midia aplicadas no Supabase;
- pelo menos 1 item com `video_url` valido;
- pelo menos 1 item com `image_urls` valido;
- workflow Instagram importado e `active=false`;
- target `oferta.femininas` presente na allowlist/config;
- credenciais da Instagram Graph API configuradas no ambiente operacional, fora
  do Git.

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

- ate 3 Reels por dia, nas janelas 10:00, 14:00 e 18:00 BRT;
- nichos preferenciais: `maquiagem-geral`, `skincare-facial` e
  `acessorios-femininos`;
- 1 carrossel diario para moda quando houver midia valida;
- fallback sempre pela ordem materializada em `offers.daily_dispatch_plan`;
- sem publicacao automatica em massa;
- sem download, transcodificacao ou hospedagem propria de midia.

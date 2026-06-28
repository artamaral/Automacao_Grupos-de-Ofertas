# Workflow n8n implementavel

Este documento descreve uma versao implementavel do workflow no `n8n`, com
nomes sugeridos de nos, tipos de nos, comandos e contratos de entrada e saida.

Ele complementa:

- [`docs/n8n-workflow.md`](n8n-workflow.md)
- [`docs/runbook-n8n.md`](runbook-n8n.md)

Um esqueleto inicial em JSON para montagem no `n8n` esta em
[`n8n/workflows/ofertas-rodada-skeleton.json`](../n8n/workflows/ofertas-rodada-skeleton.json).

## Premissas

- o `n8n` roda no mesmo ambiente onde os scripts operacionais estao
  disponiveis;
- o projeto esta disponivel em `<n8n-root>/app/Automacao_Grupos-de-Ofertas`;
- os catalogos ativos estao em `<n8n-root>/catalogs/<profile>/`;
- os artefatos da rodada ficam em `<n8n-root>/data/<profile>/`;
- a fase continua em `dry-run`.

## Variaveis base do workflow

Configure estes valores no inicio do fluxo:

```text
root_dir = <n8n-root>
app_dir = <n8n-root>/app/Automacao_Grupos-de-Ofertas
catalogs_dir = <n8n-root>/catalogs
data_dir = <n8n-root>/data
```

Campos por execucao:

```text
profile
run_id
requested_by
notes
profile_catalog
profile_data_dir
```

## Trigger recomendado

### No 01 - Trigger Rodada

Tipo:

- `Manual Trigger` no inicio
- depois pode virar `Cron` ou `Webhook`

Payload minimo:

```json
{
  "profile": "feminino",
  "run_id": "2026-06-28-feminino-01",
  "requested_by": "arthur",
  "notes": "rodada manual"
}
```

## Nos de contexto e validacao

### No 02 - Set Contexto Base

Tipo:

- `Set`

Campos a criar:

```json
{
  "profile": "={{ $json.profile }}",
  "run_id": "={{ $json.run_id }}",
  "requested_by": "={{ $json.requested_by || 'n8n' }}",
  "notes": "={{ $json.notes || '' }}",
  "root_dir": "<n8n-root>",
  "app_dir": "<n8n-root>/app/Automacao_Grupos-de-Ofertas",
  "catalogs_dir": "<n8n-root>/catalogs",
  "data_dir": "<n8n-root>/data",
  "profile_catalog": "={{ '<n8n-root>/catalogs/' + $json.profile + '/clean_catalog_rating_4_8_plus.csv' }}",
  "profile_data_dir": "={{ '<n8n-root>/data/' + $json.profile }}"
}
```

Saida esperada:

- um item com todo o contexto de execucao

### No 03 - Validar Profile

Tipo:

- `IF`

Regra:

```text
profile in ['feminino', 'mae-e-bebe', 'auto-e-moto']
```

Ramo verdadeiro:

- segue fluxo

Ramo falso:

- vai para no de erro `Erro Profile Invalido`

### No 04 - Erro Profile Invalido

Tipo:

- `Set` ou `Code`

Payload sugerido:

```json
{
  "status": "error",
  "error_code": "invalid_profile",
  "message": "profile fora do contrato operacional"
}
```

## Nos de preparacao de ambiente

### No 05 - Garantir Pasta do Profile

Tipo:

- `Execute Command`

Comando:

```powershell
New-Item -ItemType Directory -Force -Path "{{$json.profile_data_dir}}" | Out-Null
```

Workdir:

- qualquer

Saida esperada:

- exit code `0`

### No 06 - Validar Catalogo Ativo

Tipo:

- `Execute Command`

Comando:

```powershell
powershell -ExecutionPolicy Bypass -File "{{$json.root_dir}}\app\Automacao_Grupos-de-Ofertas\scripts\n8n\validate_catalog.ps1" -Profile "{{$json.profile}}" -RootDir "{{$json.root_dir}}"
```

Ramo de erro:

- notificar operador para atualizar catalogo

## Nos de prepare

### No 07 - Montar Comando Prepare

Tipo:

- `Set`

Campo sugerido:

```json
{
  "prepare_command": "={{ 'powershell -ExecutionPolicy Bypass -File \"' + $json.app_dir + '\\scripts\\n8n\\invoke_prepare.ps1\" -Profile \"' + $json.profile + '\" -RootDir \"' + $json.root_dir + '\"' }}"
}
```

### No 08 - Executar Prepare

Tipo:

- `Execute Command`

Comando:

```powershell
{{$json.prepare_command}}
```

Workdir:

- `={{ $json.app_dir }}`

Capturar:

- stdout
- stderr
- exit code

### No 09 - Validar Artefatos Prepare

Tipo:

- `Execute Command`

Comando:

```powershell
$base = "{{$json.profile_data_dir}}"
$required = @(
  "offers.json",
  "selection_state.json",
  "copy_briefs.json",
  "messages_preview.html",
  "review_queue.json"
)
$missing = @()
foreach ($name in $required) {
  $path = Join-Path $base $name
  if (!(Test-Path $path)) { $missing += $name }
}
if ($missing.Count -gt 0) {
  Write-Error ("MISSING=" + ($missing -join ","))
  exit 1
}
Write-Output "PREPARE_OUTPUTS_OK"
```

Se falhar:

- parar rodada
- registrar erro `prepare_outputs_missing`

## Nos de revisao

### No 10 - Carregar Review Queue

Tipo:

- `Read File`
- ou `Execute Command` lendo JSON

Arquivo:

```text
{{$json.profile_data_dir}}/review_queue.json
```

Saida:

- conteudo da fila em JSON

### No 11 - Publicar Pendencia de Revisao

Tipo:

- `Email`, `Slack`, `WhatsApp`, `Telegram` ou `Set`

Mensagem minima:

```text
Rodada {{$json.run_id}} do profile {{$json.profile}} aguardando revisao.
Fila: {{$json.profile_data_dir}}/review_queue.json
```

Saida esperada:

```json
{
  "review_status": "awaiting_human_review"
}
```

### No 12 - Wait Review

Tipo:

- `Wait`

Modo sugerido:

- pausar e retomar manualmente
- ou retomar via `Webhook`

## Nos de validacao da revisao

### No 13 - Validar Queue Resolvida

Tipo:

- `Execute Command`

Comando:

```powershell
$path = "{{$json.profile_data_dir}}\\review_queue.json"
$items = Get-Content $path -Raw | ConvertFrom-Json
$pending = @($items | Where-Object { $_.status -eq "pending" }).Count
Write-Output "PENDING_COUNT=$pending"
if ($pending -gt 0) { exit 2 }
```

Tratamento:

- `exit 0`: seguir
- `exit 2`: voltar para espera ou encerrar com `review_incomplete`
- `exit 1`: erro de leitura ou formato

## Nos de finalize

### No 14 - Montar Comando Finalize

Tipo:

- `Set`

Campo sugerido:

```json
{
  "finalize_command": "={{ 'powershell -ExecutionPolicy Bypass -File \"' + $json.app_dir + '\\scripts\\n8n\\invoke_finalize.ps1\" -Profile \"' + $json.profile + '\" -RootDir \"' + $json.root_dir + '\"' }}"
}
```

### No 15 - Executar Finalize

Tipo:

- `Execute Command`

Comando:

```powershell
{{$json.finalize_command}}
```

Workdir:

- `={{ $json.app_dir }}`

Capturar:

- stdout
- stderr
- exit code

### No 16 - Validar Artefatos Finalize

Tipo:

- `Execute Command`

Comando:

```powershell
$base = "{{$json.profile_data_dir}}"
$required = @(
  "approved_messages.json",
  "publication_manifest.json",
  "dispatch_artifact.json",
  "dispatch_report.json"
)
$missing = @()
foreach ($name in $required) {
  $path = Join-Path $base $name
  if (!(Test-Path $path)) { $missing += $name }
}
if ($missing.Count -gt 0) {
  Write-Error ("MISSING=" + ($missing -join ","))
  exit 1
}
Write-Output "FINALIZE_OUTPUTS_OK"
```

## Nos de leitura e resumo final

### No 17 - Ler Dispatch Artifact

Tipo:

- `Read File`

Arquivo:

```text
{{$json.profile_data_dir}}/dispatch_artifact.json
```

Saida:

- objeto JSON do dispatch

### No 18 - Ler Dispatch Report

Tipo:

- `Read File`

Arquivo:

```text
{{$json.profile_data_dir}}/dispatch_report.json
```

Saida:

- objeto JSON do relatorio

### No 19 - Montar Resumo da Rodada

Tipo:

- `Code`

Responsabilidade:

- ler `dispatch_artifact` e `dispatch_report`
- emitir resumo operacional

Exemplo de saida:

```json
{
  "status": "ok",
  "profile": "feminino",
  "run_id": "2026-06-28-feminino-01",
  "dispatch_artifact_path": "<n8n-root>/data/feminino/dispatch_artifact.json",
  "dispatch_report_path": "<n8n-root>/data/feminino/dispatch_report.json",
  "total_targets": 2,
  "total_available_messages": 6,
  "total_selected_messages": 6,
  "total_blocked_targets": 0,
  "mode": "dry-run"
}
```

## Nos de persistencia e notificacao

### No 20 - Persistir Log da Rodada

Tipo:

- `Write File`
- `Database`
- `Google Sheets`
- `Notion`

Payload recomendado:

- `profile`
- `run_id`
- `status`
- `mode`
- `total_targets`
- `total_selected_messages`
- `total_blocked_targets`
- `requested_by`

### No 21 - Notificar Conclusao

Tipo:

- `Email`
- `Slack`
- `WhatsApp`
- `Telegram`

Mensagem sugerida:

```text
Rodada {{$json.run_id}} do profile {{$json.profile}} concluida em dry-run.
Mensagens selecionadas: {{$json.total_selected_messages}}
Destinos: {{$json.total_targets}}
Bloqueios: {{$json.total_blocked_targets}}
```

## Branches de erro implementaveis

## Branch A - Catalogo ausente

Origem:

- no `Validar Catalogo Ativo`

Acao:

1. gravar erro estruturado
2. notificar operador
3. encerrar workflow

Payload sugerido:

```json
{
  "status": "error",
  "error_code": "catalog_missing",
  "profile": "feminino"
}
```

## Branch B - Prepare falhou

Origem:

- no `Executar Prepare`

Acao:

1. capturar stderr
2. registrar erro
3. notificar operador
4. encerrar workflow

## Branch C - Revisao incompleta

Origem:

- no `Validar Queue Resolvida`

Acao:

1. marcar `review_incomplete`
2. voltar para espera
3. ou encerrar com status de pendencia

## Branch D - Finalize falhou

Origem:

- no `Executar Finalize`

Acao:

1. capturar stderr
2. registrar erro
3. notificar operador
4. encerrar workflow

## Mapa resumido dos nos

```text
01 Trigger Rodada
02 Set Contexto Base
03 Validar Profile
04 Erro Profile Invalido
05 Garantir Pasta do Profile
06 Validar Catalogo Ativo
07 Montar Comando Prepare
08 Executar Prepare
09 Validar Artefatos Prepare
10 Carregar Review Queue
11 Publicar Pendencia de Revisao
12 Wait Review
13 Validar Queue Resolvida
14 Montar Comando Finalize
15 Executar Finalize
16 Validar Artefatos Finalize
17 Ler Dispatch Artifact
18 Ler Dispatch Report
19 Montar Resumo da Rodada
20 Persistir Log da Rodada
21 Notificar Conclusao
```

## Ordem de implantacao recomendada

1. montar nos `01` a `09`
2. validar `prepare` para `feminino`
3. montar nos `10` a `13`
4. validar pausa e retomada de revisao
5. montar nos `14` a `21`
6. validar `finalize`
7. repetir com `mae-e-bebe`
8. repetir com `auto-e-moto`

## Fora do escopo desta versao

Ainda nao entra nesta versao:

- envio real por `WhatsApp`
- sessao autenticada
- webhook de entrega real
- `ENABLE_REAL_PUBLISH=true`

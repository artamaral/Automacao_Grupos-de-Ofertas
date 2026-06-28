# Workflow n8n implementavel

Este documento descreve a versao implementavel das duas trilhas de `n8n`:

- `self-hosted/local`
- `hosted/cloud` por HTTP

A trilha atual continua sendo a local. A trilha cloud foi criada em paralelo para
nao precisarmos redesenhar o fluxo quando quisermos operar tudo de forma
autonoma.

Arquivos centrais:

- [`n8n/workflows/ofertas-rodada-self-hosted-skeleton.json`](../n8n/workflows/ofertas-rodada-self-hosted-skeleton.json)
- [`n8n/workflows/ofertas-rodada-skeleton.json`](../n8n/workflows/ofertas-rodada-skeleton.json)
- [`docs/n8n-cloud-runner.md`](n8n-cloud-runner.md)

## Regra operacional

O contrato default e automatico.

Isso significa:

- `review_queue.json` nao bloqueia mais o fluxo;
- `prepare` ja deixa a fila tecnicamente pronta;
- `finalize` nao depende de aprovacao humana;
- qualquer etapa manual futura fica fora do contrato minimo.

## 1. Trilha self-hosted/local

Quando usar:

- `n8n` no mesmo host do projeto
- nodes de comando disponiveis
- acesso ao filesystem local

Passos:

1. validar catalogo local
2. executar `prepare`
3. validar artefatos de `prepare`
4. executar `finalize`
5. validar artefatos finais
6. consolidar resumo

Essa trilha continua suportada pelo workflow:

- [`n8n/workflows/ofertas-rodada-self-hosted-skeleton.json`](../n8n/workflows/ofertas-rodada-self-hosted-skeleton.json)

## 2. Trilha hosted/cloud por HTTP

Quando usar:

- `n8n` hospedado
- ausencia de `Execute Command`
- necessidade de automacao de ponta a ponta

### Nos do skeleton hospedado

#### No 01 - Trigger Rodada

Tipo:

- `Manual Trigger` no inicio
- depois pode virar `Cron` ou `Webhook`

Payload base:

```json
{
  "profiles_csv": "feminino,mae-e-bebe,auto-e-moto",
  "run_id": "2026-06-28-janela-01",
  "requested_by": "arthur",
  "notes": "rodada controlada",
  "runner_base_url": "https://SEU-RUNNER-HTTP",
  "allowed_targets_csv": "grupo-teste-controlado"
}
```

#### No 02 - Set Contexto Base

Campos criados:

- `profiles_csv`
- `run_id`
- `requested_by`
- `notes`
- `allowed_targets_csv`
- `runner_base_url`
- `root_dir`
- `app_dir`

#### No 03 - Validar Contexto

Tipo:

- `Code`

Valida:

- `runner_base_url` presente
- `profiles_csv` nao vazio
- profiles dentro do contrato

#### No 04 - Health Runner

Tipo:

- `HTTP Request`

Chamada:

```http
GET {{runner_base_url}}/health
```

Objetivo:

- confirmar que o runner HTTP esta de pe antes da rodada

#### No 05 - Prepare Window

Tipo:

- `HTTP Request`

Chamada:

```http
POST {{runner_base_url}}/prepare-window
Content-Type: application/json
```

Body:

```json
{
  "profiles_csv": "feminino,mae-e-bebe,auto-e-moto",
  "run_id": "2026-06-28-janela-01",
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas"
}
```

Objetivo:

- disparar `prepare` para todos os perfis da janela

#### No 06 - Finalizar Window

Tipo:

- `HTTP Request`

Chamada:

```http
POST {{runner_base_url}}/finalize-window
Content-Type: application/json
```

Body igual ao `prepare`.

Objetivo:

- disparar o `finalize` automatico da janela

#### No 07 - Dispatch Window

Tipo:

- `HTTP Request`

Chamada:

```http
POST {{runner_base_url}}/dispatch-window
Content-Type: application/json
```

Body:

```json
{
  "profiles_csv": "feminino,mae-e-bebe,auto-e-moto",
  "run_id": "2026-06-28-janela-01",
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas",
  "allowed_targets_csv": "grupo-teste-controlado"
}
```

Objetivo:

- devolver para o `n8n` apenas as mensagens prontas para o teste controlado;
- limitar a entrega real ao destino explicitamente permitido.

#### No 08 - Enviar no Canal Real

Tipo:

- node do provedor real de `WhatsApp` escolhido na instancia do `n8n`

Entrada:

- cada item de `deliveries[]` vindo do `dispatch-window`

Objetivo:

- enviar a mensagem real no grupo de teste;
- devolver sucesso ou falha por mensagem.

#### No 09 - Confirmar Entrega

Tipo:

- `HTTP Request`

Chamada:

```http
POST {{runner_base_url}}/confirm-delivery
Content-Type: application/json
```

Body minimo:

```json
{
  "profile": "feminino",
  "target": "grupo-teste-controlado",
  "manifest_item_number": 1,
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas"
}
```

Objetivo:

- atualizar `last_sent_at` apenas da mensagem efetivamente enviada.

#### No 10 - Montar Resumo da Rodada

Tipo:

- `Code`

Saida esperada:

- `run_id`
- `profiles_csv`
- `runner_base_url`
- `allowed_targets_csv`
- `prepare_summary_path`
- `finalize_summary_path`
- `dispatch_total_targets`
- `dispatch_total_deliveries`
- `prepare_profiles`
- `finalize_profiles`
- `dispatch_profiles`
- `deliveries`

#### Nos 11 e 12

Tipos:

- `Set`

Estado atual:

- placeholders para persistencia e notificacao reais

## 3. Cloud runner do projeto

Entry point:

```text
ofertas-cloud-runner
```

Implementacao:

- [`src/ofertas_bot/cloud_runner.py`](../src/ofertas_bot/cloud_runner.py)
- [`src/ofertas_bot/cloud_runner_server.py`](../src/ofertas_bot/cloud_runner_server.py)

Endpoints:

- `GET /health`
- `POST /prepare-window`
- `POST /finalize-window`
- `POST /dispatch-window`
- `POST /run-window`
- `POST /confirm-delivery`
- `POST /confirm-window-deliveries`

Payloads versionados:

- [`n8n/payloads/ofertas-janela-multi-profile.example.json`](../n8n/payloads/ofertas-janela-multi-profile.example.json)
- [`n8n/payloads/prepare-window-runner.example.json`](../n8n/payloads/prepare-window-runner.example.json)
- [`n8n/payloads/finalize-window-runner.example.json`](../n8n/payloads/finalize-window-runner.example.json)
- [`n8n/payloads/run-window-runner.example.json`](../n8n/payloads/run-window-runner.example.json)
- [`n8n/payloads/confirm-window-deliveries-runner.example.json`](../n8n/payloads/confirm-window-deliveries-runner.example.json)

## 4. O que permanece igual entre as duas trilhas

- perfis permitidos
- score e selecao
- copy briefs gerados
- HTML preview gerado
- manifesto e dispatch final
- ausencia de validacao humana obrigatoria

## 5. O que muda entre as duas trilhas

### Self-hosted/local

- executa script local
- depende de host e filesystem
- menor distancia da implementacao atual

### Hosted/cloud

- executa por HTTP
- nao depende de node de comando no `n8n`
- preparada para operacao autonoma futura

## 6. Fora do escopo desta fase

Ainda nao entra nesta fase:

- storage realmente cloud-native
- publisher real dentro do Python

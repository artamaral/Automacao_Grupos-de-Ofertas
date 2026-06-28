# Runbook n8n

Este runbook descreve como operar o projeto com `n8n` nas duas trilhas hoje
suportadas pelo repositorio:

- `self-hosted/local`: trilha atual, usando scripts locais
- `hosted/cloud`: trilha paralela, usando `cloud runner` HTTP

Documentos complementares:

- [`docs/n8n-workflow.md`](n8n-workflow.md)
- [`docs/n8n-workflow-implementavel.md`](n8n-workflow-implementavel.md)
- [`docs/n8n-cloud-runner.md`](n8n-cloud-runner.md)
- [`docs/n8n-validation.md`](n8n-validation.md)

## Decisao operacional atual

O fluxo principal e automatico.

Portanto:

- `review_queue.json` permanece como artefato tecnico;
- `prepare` nao cria mais dependencia de validacao humana;
- `finalize` pode seguir automaticamente no contrato default;
- qualquer gate manual futuro sera opcional.

## 1. Artefatos oficiais

### Workflow hosted/cloud

- [`n8n/workflows/ofertas-rodada-skeleton.json`](../n8n/workflows/ofertas-rodada-skeleton.json)

### Workflow self-hosted/local

- [`n8n/workflows/ofertas-rodada-self-hosted-skeleton.json`](../n8n/workflows/ofertas-rodada-self-hosted-skeleton.json)

### Payloads de exemplo

- [`n8n/payloads/ofertas-janela-multi-profile.example.json`](../n8n/payloads/ofertas-janela-multi-profile.example.json)
- [`n8n/payloads/prepare-window-runner.example.json`](../n8n/payloads/prepare-window-runner.example.json)
- [`n8n/payloads/finalize-window-runner.example.json`](../n8n/payloads/finalize-window-runner.example.json)

## 2. Perfis permitidos

- `feminino`
- `mae-e-bebe`
- `auto-e-moto`

## 3. Trilha self-hosted/local

Use esta trilha quando o `n8n` conseguir acessar o host e executar comandos.

### Estrutura base

```text
C:\Automacao_Grupos-de-Ofertas\n8n\root\
  catalogs\<profile>\clean_catalog_rating_4_8_plus.csv
  data\<profile>\
  logs\
```

### Variaveis base

```text
N8N_OFERTAS_ROOT=C:\Automacao_Grupos-de-Ofertas\n8n\root
N8N_OFERTAS_APP=C:\Automacao_Grupos-de-Ofertas
N8N_OFERTAS_CATALOGS=C:\Automacao_Grupos-de-Ofertas\n8n\root\catalogs
N8N_OFERTAS_DATA=C:\Automacao_Grupos-de-Ofertas\n8n\root\data
```

### Passos

1. importar `ofertas-rodada-self-hosted-skeleton.json`
2. subir catalogos ativos em `n8n/root/catalogs/<profile>/`
3. executar `prepare`
4. validar artefatos
5. executar `finalize`
6. validar `dispatch_artifact.json`

## 4. Trilha hosted/cloud

Use esta trilha quando o `n8n` for hospedado e nao tiver `Execute Command`.

### Contrato

O `n8n` fala com um runner HTTP do projeto:

- `GET /health`
- `POST /prepare-window`
- `POST /finalize-window`

### Entry point do runner

```text
ofertas-cloud-runner
```

### Passos

1. publicar o runner HTTP em um ambiente proprio
2. garantir acesso do runner ao app e aos catalogos
3. importar `ofertas-rodada-skeleton.json`
4. configurar `runner_base_url`
5. disparar a rodada pelo payload da janela

### Payload base do workflow hosted

```json
{
  "profiles_csv": "feminino,mae-e-bebe,auto-e-moto",
  "run_id": "2026-06-28-janela-01",
  "requested_by": "arthur",
  "notes": "rodada dry-run",
  "runner_base_url": "https://SEU-RUNNER-HTTP",
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas"
}
```

## 5. Saidas esperadas

### Prepare

- `offers.json`
- `selection_state.json`
- `copy_briefs.json`
- `messages_preview.html`
- `review_queue.json`

### Finalize

- `approved_messages.json`
- `publication_manifest.json`
- `dispatch_artifact.json`
- `dispatch_report.json`

## 6. Regra de horizontalizacao

Toda evolucao do fluxo principal deve respeitar:

- o contrato funcional precisa permanecer equivalente nas duas trilhas;
- a unica diferenca estrutural aceita e o meio de execucao:
  - script local
  - HTTP
- melhorias em score, selecao, copy e dispatch devem refletir nas duas.

## 7. Estado desta fase

Hoje o repositorio fica assim:

- a solucao local continua sendo a oficial e operacional;
- a solucao cloud foi criada em paralelo para uso futuro;
- nenhuma das duas depende de validacao humana obrigatoria;
- o proximo salto natural e hospedar o `cloud runner` e ligar persistencia/notificacao reais no `n8n`.

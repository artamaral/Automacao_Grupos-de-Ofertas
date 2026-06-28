# Workflow n8n

Este documento desenha o workflow recomendado no `n8n` para operar o fluxo
principal.

Ele complementa:

- [`docs/runbook-n8n.md`](runbook-n8n.md)
- [`docs/contrato-n8n-whatsapp.md`](contrato-n8n-whatsapp.md)

A versao implementavel, com nos e comandos sugeridos, esta em
[`docs/n8n-workflow-implementavel.md`](n8n-workflow-implementavel.md).

A arquitetura para processar `N` nichos e `N` grupos na mesma execucao esta em
[`docs/n8n-arquitetura-multi-nicho.md`](n8n-arquitetura-multi-nicho.md).

## Objetivo do workflow

Executar uma janela operacional unica dentro do `n8n`, processando uma lista de
`profiles` no mesmo run e mantendo:

- catalogo ativo no ambiente do `n8n`;
- artefatos da rodada no ambiente do `n8n`;
- revisao humana antes do `finalize`;
- saida final em `dispatch_artifact.json`;
- nenhuma publicacao real nesta fase.

## Perfis permitidos

- `feminino`
- `mae-e-bebe`
- `auto-e-moto`

## Estrutura logica do workflow

```text
Trigger
  -> Expandir profiles da janela
  -> Para cada profile:
       Validar profile e paths
       Validar catalogo ativo
       Executar prepare
       Validar artefatos de prepare
       Publicar fila para revisao
       Esperar decisao humana
       Validar queue sem pendencias
       Executar finalize
       Validar artefatos finais
       Montar resumo do profile
  -> Consolidar resumo da janela
  -> Registrar resultado
```

## Variaveis base

Campos de entrada da execucao:

- `profiles_csv`
- `run_id`
- `requested_by`
- `notes`

Campos calculados:

- `root_dir`
- `app_dir`
- `catalogs_dir`
- `data_dir`
- `profile_catalog`
- `profile_data_dir`
- `prepare_command`
- `finalize_command`

## Blueprint dos nos

## 1. Trigger

Tipo sugerido:

- Manual Trigger
- Cron
- Webhook

Entrada minima:

```json
{
  "profile": "feminino",
  "run_id": "2026-06-28-feminino-01"
}
```

Responsabilidade:

- iniciar a rodada;
- definir o `profile`;
- gerar ou receber `run_id`.

## 2. Set Context

Tipo sugerido:

- Set

Responsabilidade:

- montar paths e metadados da execucao.

Saida esperada:

```json
{
  "profile": "feminino",
  "run_id": "2026-06-28-feminino-01",
  "root_dir": "<n8n-root>",
  "app_dir": "<n8n-root>/app/Automacao_Grupos-de-Ofertas",
  "catalogs_dir": "<n8n-root>/catalogs",
  "data_dir": "<n8n-root>/data",
  "profile_catalog": "<n8n-root>/catalogs/feminino/clean_catalog_rating_4_8_plus.csv",
  "profile_data_dir": "<n8n-root>/data/feminino"
}
```

## 3. Validate Profile

Tipo sugerido:

- IF

Regra:

- permitir apenas `feminino`, `mae-e-bebe`, `auto-e-moto`

Se falhar:

- encerrar com erro operacional

## 4. Ensure Directories

Tipo sugerido:

- Execute Command

Responsabilidade:

- garantir que a pasta de dados do `profile` exista no ambiente do `n8n`.

Exemplo:

```powershell
New-Item -ItemType Directory -Force -Path "<n8n-root>\data\feminino" | Out-Null
```

## 5. Validate Catalog

Tipo sugerido:

- Execute Command
- ou Read Binary File / filesystem check

Responsabilidade:

- confirmar existencia do catalogo ativo do `profile`.

Validacao:

- arquivo existe
- arquivo nao esta vazio

Se falhar:

- parar a rodada;
- notificar operador para atualizar catalogo.

## 6. Execute Prepare

Tipo sugerido:

- Execute Command

Comando base:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --profile feminino --data-dir <n8n-root>/data/feminino --catalog-file <n8n-root>/catalogs/feminino/clean_catalog_rating_4_8_plus.csv
```

Workdir:

- `<n8n-root>/app/Automacao_Grupos-de-Ofertas`

Responsabilidade:

- gerar a rodada;
- aplicar score e selecao;
- gerar fila de revisao.

## 7. Validate Prepare Outputs

Tipo sugerido:

- Execute Command
- ou IF + filesystem checks

Arquivos obrigatorios:

- `offers.json`
- `selection_state.json`
- `copy_briefs.json`
- `messages_preview.html`
- `review_queue.json`

Se algum faltar:

- parar a rodada;
- registrar falha.

## 8. Load Review Queue

Tipo sugerido:

- Read File
- Move Binary Data / JSON parse

Arquivo:

- `<n8n-root>/data/<profile>/review_queue.json`

Responsabilidade:

- carregar a fila para revisao humana;
- expor conteudo para a proxima etapa.

## 9. Publish Review Task

Tipo sugerido:

- Email
- WhatsApp interno de aprovacao
- Slack
- Notion
- banco interno
- UI manual do proprio n8n

Responsabilidade:

- avisar que a rodada aguarda revisao;
- incluir `profile`, `run_id` e path da fila.

Saida minima:

- status `awaiting_review`

## 10. Wait for Human Review

Tipo sugerido:

- Wait
- Webhook resume
- Manual approval gate

Responsabilidade:

- pausar o fluxo ate a revisao terminar.

Condicao de retomada:

- operador concluiu aprovacoes/rejeicoes

## 11. Validate Queue Resolved

Tipo sugerido:

- Execute Command
- ou leitura + IF

Responsabilidade:

- garantir que nao existe item `pending` em `review_queue.json`

Se ainda existir pendencia:

- voltar para espera;
- ou encerrar com status `review_incomplete`

## 12. Execute Finalize

Tipo sugerido:

- Execute Command

Comando base:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize --profile feminino --data-dir <n8n-root>/data/feminino
```

Workdir:

- `<n8n-root>/app/Automacao_Grupos-de-Ofertas`

Responsabilidade:

- exportar aprovadas;
- gerar manifesto;
- gerar `dispatch_artifact.json`;
- gerar `dispatch_report.json`;
- atualizar `last_sent_at`.

## 13. Validate Final Outputs

Tipo sugerido:

- Execute Command
- ou IF + filesystem checks

Arquivos obrigatorios:

- `approved_messages.json`
- `publication_manifest.json`
- `dispatch_artifact.json`
- `dispatch_report.json`

Se algum faltar:

- parar a rodada;
- registrar falha.

## 14. Load Dispatch Artifact

Tipo sugerido:

- Read File
- JSON parse

Arquivo:

- `<n8n-root>/data/<profile>/dispatch_artifact.json`

Responsabilidade:

- carregar o artefato final da rodada;
- expor mensagens prontas por destino logico.

## 15. Summarize Run

Tipo sugerido:

- Code
- Set

Responsabilidade:

- montar um resumo final da rodada.

Campos recomendados:

- `profile`
- `run_id`
- `prepare_ok`
- `finalize_ok`
- `dispatch_targets`
- `total_available_messages`
- `total_selected_messages`
- `total_blocked_targets`
- `dispatch_artifact_path`
- `dispatch_report_path`

## 16. Persist Run Log

Tipo sugerido:

- Write File
- Database
- Google Sheets
- Notion

Responsabilidade:

- registrar o resultado da rodada para auditoria operacional.

## 17. Notify Completion

Tipo sugerido:

- Email
- WhatsApp
- Telegram
- Slack

Responsabilidade:

- informar que a rodada terminou;
- enviar resumo;
- destacar se houve bloqueio por quiet period.

## Branches de erro

O workflow deve prever ao menos estes ramos:

### Erro 1: profile invalido

Acao:

- encerrar imediatamente

### Erro 2: catalogo ausente

Acao:

- encerrar
- notificar operador para atualizar catalogo

### Erro 3: prepare falhou

Acao:

- registrar stderr
- notificar falha operacional

### Erro 4: revisao nao concluida

Acao:

- manter workflow pausado
- ou encerrar com status de pendencia

### Erro 5: finalize falhou

Acao:

- registrar stderr
- notificar falha operacional

## Dados que o n8n deve tratar como somente leitura

O `n8n` nao deve reescrever manualmente:

- score
- reasons
- copy
- manifesto
- dispatch artifact
- selection state

Excecao operacional desta fase:

- a revisao humana pode mudar status da `review_queue`

## Ponto do operador

O operador participa em dois pontos:

1. atualizar o catalogo ativo no `n8n`
2. concluir a revisao humana da `review_queue.json`

## Ordem de implementacao recomendada

1. criar workflow para `feminino`
2. validar `prepare`
3. validar pausa para revisao
4. validar `finalize`
5. validar leitura de `dispatch_artifact.json`
6. repetir sem mudanca estrutural para `mae-e-bebe`
7. repetir sem mudanca estrutural para `auto-e-moto`

## Resultado esperado

Ao final desta fase, o `n8n` deve conseguir:

- rodar uma rodada por `profile`
- manter os artefatos no proprio ambiente
- aguardar revisao humana
- consolidar a rodada
- produzir `dispatch_artifact.json`

Sem:

- envio real
- sessao real de `WhatsApp`
- `ENABLE_REAL_PUBLISH=true`

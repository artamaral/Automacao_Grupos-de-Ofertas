# Validacao n8n

Este documento registra a validacao local dos wrappers e do contrato
operacional pensado para o `n8n`.

## Objetivo

Confirmar que os wrappers implementados em [`scripts/n8n/`](../scripts/n8n/)
conseguem operar um `n8n-root` de teste com:

- catalogo ativo por `profile`
- dados de rodada por `profile`
- `prepare`
- revisao resolvida
- `finalize`
- dispatch bloqueado por quiet period
- dispatch liberado por horario forcado

## Ambiente de teste

Raiz usada no teste:

```text
tmp/n8n-root-test
```

Profile validado:

- `feminino`

Estrutura preparada:

```text
tmp/n8n-root-test/catalogs/feminino/clean_catalog_rating_4_8_plus.csv
tmp/n8n-root-test/data/feminino/
```

## Wrappers validados

- [`scripts/n8n/validate_catalog.ps1`](../scripts/n8n/validate_catalog.ps1)
- [`scripts/n8n/invoke_prepare.ps1`](../scripts/n8n/invoke_prepare.ps1)
- [`scripts/n8n/invoke_finalize.ps1`](../scripts/n8n/invoke_finalize.ps1)

## Resultado 1: validacao de catalogo

Comando validado:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\validate_catalog.ps1 -Profile feminino -RootDir <n8n-root>
```

Resultado:

- `OK`
- catalogo encontrado
- catalogo nao vazio

## Resultado 2: prepare

Comando validado:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\invoke_prepare.ps1 -Profile feminino -RootDir <n8n-root>
```

Resultado:

- `OK`
- `prepare` executado com sucesso
- artefatos principais gerados em `data/feminino`

Artefatos confirmados:

- `offers.json`
- `selection_state.json`
- `copy_briefs.json`
- `messages_preview.html`
- `review_queue.json`
- `review_plan.json`

Observacao:

- a rodada produziu `20` ofertas selecionadas para copy
- a fila de revisao expandiu por destino e gerou `40` entradas aprovaveis

## Resultado 3: finalize em horario real do teste

Comando validado:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\invoke_finalize.ps1 -Profile feminino -RootDir <n8n-root>
```

Resultado:

- `OK`
- artefatos finais gerados
- nenhum erro de wrapper

Artefatos confirmados:

- `approved_messages.json`
- `publication_manifest.json`
- `dispatch_artifact.json`
- `dispatch_report.json`
- `local_review_bundle.json`

Resultado operacional do dispatch nessa execucao:

- `total_targets = 2`
- `total_available_messages = 40`
- `total_selected_messages = 0`
- `total_blocked_targets = 2`

Motivo:

- os dois destinos ficaram bloqueados por `quiet_period_active`

Conclusao:

- zero mensagens selecionadas nao foi falha de implementacao
- foi comportamento correto da regra de horario

## Resultado 4: finalize simulado com horario forcado

Horario forcado:

```text
2026-06-28T14:00:00-03:00
```

Resultado do `dispatch_artifact` forcado:

- `total_targets = 2`
- `total_available_messages = 40`
- `total_selected_messages = 6`
- `total_skipped_messages = 34`
- `total_blocked_targets = 0`

Quebra por destino:

- `canal-beleza`: `20` disponiveis, `3` selecionadas
- `grupo-beleza`: `20` disponiveis, `3` selecionadas

Conclusao:

- fora da janela de silencio, a selecao do dispatch funcionou corretamente
- o contrato do artifact e do report permaneceu consistente

## Resultado 5: atualizacao de estado

O `selection_state.json` permaneceu consistente durante o teste.

Estado observado:

- `20` registros no total
- `20` registros com `selection_count`
- `3` registros com `last_sent_at` apos a simulacao forcada

Importante:

- o dispatch forcado selecionou `6` mensagens
- mas elas representavam `3` ofertas unicas repetidas em `2` destinos
- como `selection_state` e por oferta, o correto era atualizar `3` ofertas, e
  nao `6`

## Conclusao geral

O bloco implementado para `n8n` foi validado com sucesso em ambiente local de
teste:

- wrapper de catalogo: validado
- wrapper de prepare: validado
- wrapper de finalize: validado
- cenario bloqueado por quiet period: validado
- cenario liberado por horario forcado: validado
- atualizacao de `last_sent_at` por oferta: validada

## Limites desta validacao

Esta validacao ainda nao cobre:

- workflow importado no `n8n`
- notificacoes reais
- persistencia real em banco externo
- envio real por `WhatsApp`
- `ENABLE_REAL_PUBLISH=true`

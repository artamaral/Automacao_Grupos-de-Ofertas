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

Profiles validados:

- `feminino`
- `mae-e-bebe`
- `auto-e-moto`

Estrutura preparada:

```text
tmp/n8n-root-test/catalogs/feminino/clean_catalog_rating_4_8_plus.csv
tmp/n8n-root-test/data/feminino/
```

## Wrappers validados

- [`scripts/n8n/validate_catalog.ps1`](../scripts/n8n/validate_catalog.ps1)
- [`scripts/n8n/invoke_prepare.ps1`](../scripts/n8n/invoke_prepare.ps1)
- [`scripts/n8n/invoke_finalize.ps1`](../scripts/n8n/invoke_finalize.ps1)
- [`scripts/n8n/sync_catalog_to_n8n.ps1`](../scripts/n8n/sync_catalog_to_n8n.ps1)
- [`scripts/n8n/invoke_prepare_window.ps1`](../scripts/n8n/invoke_prepare_window.ps1)
- [`scripts/n8n/invoke_finalize_window.ps1`](../scripts/n8n/invoke_finalize_window.ps1)

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

## Resultado 6: sincronizacao de catalogo para raiz do n8n

Comandos validados:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\sync_catalog_to_n8n.ps1 -Profile feminino -RootDir tmp\n8n-root-test -AppDir C:\Automacao_Grupos-de-Ofertas
powershell -ExecutionPolicy Bypass -File scripts\n8n\sync_catalog_to_n8n.ps1 -Profile mae-e-bebe -RootDir tmp\n8n-root-test -AppDir C:\Automacao_Grupos-de-Ofertas
powershell -ExecutionPolicy Bypass -File scripts\n8n\sync_catalog_to_n8n.ps1 -Profile auto-e-moto -RootDir tmp\n8n-root-test -AppDir C:\Automacao_Grupos-de-Ofertas
```

Resultado:

- `OK` para os tres `profiles`
- catalogos copiados para `tmp/n8n-root-test/catalogs/<profile>/`
- metadados gerados em `catalog_sync_metadata.json` por `profile`

Conclusao:

- o operador ja tem um script unico e explicito para colocar catalogo curado
  dentro do ambiente operacional do `n8n`
- o `SourceCatalogPath` pode continuar existindo como override manual, mas o
  caminho padrao agora sai do `catalog_registry.csv`

## Resultado 7: prepare da janela multi-profile

Comando validado:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\invoke_prepare_window.ps1 -ProfilesCsv "feminino,mae-e-bebe,auto-e-moto" -RootDir tmp\n8n-root-test -AppDir C:\Automacao_Grupos-de-Ofertas -RunId 2026-06-28-janela-01
```

Resultado:

- `OK`
- `total_profiles = 3`
- resumo de janela gerado em `tmp/n8n-root-test/data/window_prepare_summary_2026-06-28-janela-01.json`

Artefatos confirmados por `profile`:

- `offers.json`
- `selection_state.json`
- `copy_briefs.json`
- `messages_preview.html`
- `review_queue.json`

Conclusao:

- o wrapper de janela consegue preparar os tres nichos no mesmo `run`
- a diferenca operacional entre nichos ficou reduzida ao valor do `profile`

## Resultado 8: finalize da janela multi-profile

Horario real da execucao:

```text
2026-06-28T08:04:31-03:00
```

Comando validado:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\invoke_finalize_window.ps1 -ProfilesCsv "feminino,mae-e-bebe,auto-e-moto" -RootDir tmp\n8n-root-test -AppDir C:\Automacao_Grupos-de-Ofertas -RunId 2026-06-28-janela-01
```

Resultado:

- `OK`
- `total_profiles = 3`
- resumo de janela gerado em `tmp/n8n-root-test/data/window_finalize_summary_2026-06-28-janela-01.json`

Resumo por `profile`:

- `feminino`
  - `approved_messages = 40`
  - `targets = 2`
  - `dispatch_report mensagens = 6`
- `mae-e-bebe`
  - `approved_messages = 80`
  - `targets = 4`
  - `dispatch_report mensagens = 16`
- `auto-e-moto`
  - `approved_messages = 80`
  - `targets = 4`
  - `dispatch_report mensagens = 16`

Conclusao:

- o wrapper de janela concluiu o `finalize` dos tres nichos no mesmo `run`
- o contrato de artefatos por `profile` permaneceu consistente ate o
  `dispatch_report`
- a validacao multi-profile ficou completa para `prepare` e `finalize`

## Resultado 9: cuidado de encoding na review queue

Durante a validacao apareceu um detalhe operacional importante:

- ao regravar `review_queue.json` com `Set-Content -Encoding utf8` no PowerShell
  classico, o arquivo pode ganhar BOM
- o loader do projeto espera JSON em `utf-8` legivel sem esse desvio

Efeito observado:

- a primeira tentativa do `finalize` multi-profile falhou com
  `Saved message review queue JSON is invalid`
- apos regravar os arquivos em UTF-8 sem BOM, o fluxo concluiu normalmente

Conclusao:

- qualquer etapa externa que regrave `review_queue.json` deve preservar JSON
  valido em UTF-8 sem alterar sua estrutura esperada pelo projeto

## Conclusao geral

O bloco implementado para `n8n` foi validado com sucesso em ambiente local de
teste:

- wrapper de catalogo: validado
- wrapper de prepare: validado
- wrapper de finalize: validado
- wrapper de sync de catalogo: validado
- wrapper de prepare da janela multi-profile: validado
- wrapper de finalize da janela multi-profile: validado
- cenario bloqueado por quiet period: validado
- cenario liberado por horario forcado: validado
- atualizacao de `last_sent_at` por oferta: validada
- cuidado de encoding da `review_queue.json`: identificado e documentado

## Limites desta validacao

Esta validacao ainda nao cobre:

- importacao real do JSON em uma instancia especifica do `n8n`
- workflow importado no `n8n`
- notificacoes reais
- persistencia real em banco externo
- envio real por `WhatsApp`
- `ENABLE_REAL_PUBLISH=true`

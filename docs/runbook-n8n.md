# Runbook n8n

Este runbook descreve como integrar e operar o fluxo principal dentro do
ambiente do `n8n`.

Ele parte das decisoes ja registradas em:

- [`docs/contrato-n8n-whatsapp.md`](contrato-n8n-whatsapp.md)
- [`docs/fluxo-operacional.md`](fluxo-operacional.md)
- [`docs/cli-rodadas.md`](cli-rodadas.md)

O desenho nodo a nodo do workflow esta em
[`docs/n8n-workflow.md`](n8n-workflow.md).

A validacao local dos wrappers e do contrato operacional esta em
[`docs/n8n-validation.md`](n8n-validation.md).

## Objetivo desta implantacao

Colocar o `n8n` como centro operacional desde o inicio, com:

- scripts operacionais disponiveis no ambiente do `n8n`;
- catalogos ativos por `profile` disponiveis no ambiente do `n8n`;
- artefatos da rodada gravados no ambiente do `n8n`;
- operador atuando apenas em pontos de atualizacao de catalogo e revisao;
- `dry-run` preservado ate existir publisher real.

## O que fica onde

### Repositorio

O repositorio continua sendo a fonte de verdade para:

- codigo;
- configuracao versionada;
- templates;
- regras de negocio;
- testes;
- documentacao.

### n8n

O `n8n` passa a ser a fonte operacional de execucao para:

- scripts efetivamente rodados pela automacao;
- catalogos ativos;
- estado da rodada;
- artefatos de prepare;
- artefatos de finalize;
- logs da automacao.

## Estrutura recomendada no ambiente do n8n

Use uma raiz operacional unica.

Exemplo:

```text
<n8n-root>/
  app/
    Automacao_Grupos-de-Ofertas/
  catalogs/
    feminino/
      clean_catalog_rating_4_8_plus.csv
    mae-e-bebe/
      clean_catalog_rating_4_8_plus.csv
    auto-e-moto/
      clean_catalog_rating_4_8_plus.csv
  data/
    feminino/
    mae-e-bebe/
    auto-e-moto/
  logs/
  scripts/
```

### Significado das pastas

- `app/`: copia operacional do projeto usada pelo `n8n`
- `catalogs/`: catalogos ativos por `profile`
- `data/`: artefatos de rodada por `profile`
- `logs/`: logs auxiliares do `n8n` ou do sistema
- `scripts/`: wrappers locais chamados pelo operador ou pelo workflow

## Estrutura de artefatos por profile

Para cada `profile`, manter:

```text
<n8n-root>/data/<profile>/offers.json
<n8n-root>/data/<profile>/selection_state.json
<n8n-root>/data/<profile>/copy_briefs.json
<n8n-root>/data/<profile>/messages.json
<n8n-root>/data/<profile>/messages.txt
<n8n-root>/data/<profile>/messages_preview.html
<n8n-root>/data/<profile>/review_queue.json
<n8n-root>/data/<profile>/review_plan.json
<n8n-root>/data/<profile>/review_plan.txt
<n8n-root>/data/<profile>/approved_messages.json
<n8n-root>/data/<profile>/approved_messages.txt
<n8n-root>/data/<profile>/approved_messages_by_group/
<n8n-root>/data/<profile>/publication_manifest.json
<n8n-root>/data/<profile>/dispatch_artifact.json
<n8n-root>/data/<profile>/dispatch_report.json
<n8n-root>/data/<profile>/dispatch_report.txt
<n8n-root>/data/<profile>/local_review_bundle.json
```

## Perfis permitidos

O `n8n` deve operar apenas estes valores:

- `feminino`
- `mae-e-bebe`
- `auto-e-moto`

Nenhum outro valor deve entrar no fluxo inicial.

## Entradas minimas do workflow

O workflow deve aceitar:

- `profile`
- `run_id`

Campos opcionais de operacao:

- `requested_by`
- `notes`
- `catalog_version`

## Variaveis recomendadas no n8n

Padronize as variaveis de ambiente ou campos internos:

```text
N8N_OFERTAS_ROOT=<n8n-root>
N8N_OFERTAS_APP=<n8n-root>/app/Automacao_Grupos-de-Ofertas
N8N_OFERTAS_CATALOGS=<n8n-root>/catalogs
N8N_OFERTAS_DATA=<n8n-root>/data
```

Variaveis calculadas por execucao:

```text
profile=<profile>
profile_data_dir=<n8n-root>/data/<profile>
profile_catalog=<n8n-root>/catalogs/<profile>/clean_catalog_rating_4_8_plus.csv
```

## Scripts que devem existir no ambiente do n8n

Minimo recomendado:

- wrapper de `prepare`
- wrapper de `finalize`
- wrapper de `prepare` da janela multi-profile
- wrapper de `finalize` da janela multi-profile
- wrapper de validacao de catalogo
- script local de atualizacao de catalogo, iniciado pelo operador

Exemplo de responsabilidade dos wrappers:

- definir `workdir`
- apontar o `--data-dir`
- apontar o `--catalog-file`
- padronizar logs e retorno

Wrappers implementados neste repositorio:

- [`scripts/n8n/invoke_prepare.ps1`](../scripts/n8n/invoke_prepare.ps1)
- [`scripts/n8n/invoke_finalize.ps1`](../scripts/n8n/invoke_finalize.ps1)
- [`scripts/n8n/invoke_prepare_window.ps1`](../scripts/n8n/invoke_prepare_window.ps1)
- [`scripts/n8n/invoke_finalize_window.ps1`](../scripts/n8n/invoke_finalize_window.ps1)
- [`scripts/n8n/validate_catalog.ps1`](../scripts/n8n/validate_catalog.ps1)
- [`scripts/n8n/sync_catalog_to_n8n.ps1`](../scripts/n8n/sync_catalog_to_n8n.ps1)
- [`scripts/n8n/common.ps1`](../scripts/n8n/common.ps1)

## Comandos base

### Prepare

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\invoke_prepare.ps1 -Profile feminino -RootDir <n8n-root>
```

### Finalize

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\invoke_finalize.ps1 -Profile feminino -RootDir <n8n-root>
```

### Validar catalogo

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\validate_catalog.ps1 -Profile feminino -RootDir <n8n-root>
```

### Prepare da janela multi-profile

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\invoke_prepare_window.ps1 -ProfilesCsv "feminino,mae-e-bebe,auto-e-moto" -RootDir <n8n-root> -RunId 2026-06-28-janela-01
```

### Finalize da janela multi-profile

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\invoke_finalize_window.ps1 -ProfilesCsv "feminino,mae-e-bebe,auto-e-moto" -RootDir <n8n-root> -RunId 2026-06-28-janela-01
```

### Sincronizar catalogo para o n8n

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\sync_catalog_to_n8n.ps1 -Profile feminino -SourceCatalogPath C:\origem\clean_catalog_rating_4_8_plus.csv -RootDir <n8n-root>
```

Regra:

- no `prepare`, o `catalog-file` deve apontar para o catalogo do `n8n`
- no `finalize`, o `data-dir` deve apontar para os artefatos do `n8n`

## Workflow recomendado no n8n

### 1. Iniciar rodada

Entrada:

- `profile`
- `run_id`

Validacoes:

- `profile` permitido
- catalogo do `profile` existe
- pasta de dados do `profile` existe ou pode ser criada

Saida:

- contexto da execucao montado

### 2. Executar prepare

Acao:

- chamar o comando `prepare`

Validar existencia de:

- `offers.json`
- `selection_state.json`
- `copy_briefs.json`
- `messages_preview.html`
- `review_queue.json`

Saida:

- rodada preparada

### 3. Publicar para revisao

Acao:

- ler `review_queue.json`
- expor a fila para revisao humana

Neste bloco, o `n8n` pode:

- apenas notificar o operador;
- abrir uma etapa manual;
- integrar uma interface externa.

Regra atual:

- nenhum item segue para `finalize` com revisao pendente.

### 4. Esperar decisao humana

Status validos por item:

- `pending`
- `approved`
- `rejected`

Condicao para continuar:

- nao pode haver item `pending`

### 5. Executar finalize

Acao:

- chamar o comando `finalize`

Validar existencia de:

- `approved_messages.json`
- `publication_manifest.json`
- `dispatch_artifact.json`
- `dispatch_report.json`

Saida:

- rodada finalizada em `dry-run`

### 6. Registrar resultado

Registrar:

- `profile`
- `run_id`
- horario de prepare
- horario de finalize
- total de mensagens disponiveis
- total de mensagens selecionadas
- total de destinos
- bloqueios por quiet period
- path do `dispatch_artifact.json`

## Contrato de arquivos que o n8n deve respeitar

### Arquivo de revisao

Fonte:

- `review_queue.json`

Uso:

- revisao humana
- gate obrigatorio antes do `finalize`

### Arquivo de manifesto

Fonte:

- `publication_manifest.json`

Uso:

- consolidacao de itens aprovados e roteados

### Arquivo de dispatch

Fonte:

- `dispatch_artifact.json`

Uso:

- artefato final da rodada
- insumo futuro do publisher real

### Arquivo de relatorio

Fonte:

- `dispatch_report.json`

Uso:

- validacao do resultado do `dry-run`
- conferencia de limites, bloqueios e volume

## Papel do operador

O operador participa em dois pontos:

### 1. Atualizacao de catalogo

O operador deve iniciar um script local que atualize o catalogo ativo do
`profile` diretamente no ambiente do `n8n`.

Responsabilidade desse script:

- copiar ou sincronizar o CSV curado para a pasta de catalogos do `n8n`
- preservar o nome padrao esperado pelo fluxo
- registrar data e origem da atualizacao

Esse item ja esta registrado no backlog em
[`docs/01_BACKLOG.md`](01_BACKLOG.md).

### 2. Revisao humana

O operador aprova ou rejeita a fila antes do `finalize`.

O operador nao deve:

- editar manifesto manualmente;
- mudar score manualmente;
- mudar `selection_state.json` manualmente;
- editar `dispatch_artifact.json` manualmente.

## Checklist de implantacao inicial no n8n

1. criar raiz operacional do `n8n`
2. disponibilizar copia operacional do projeto em `app/`
3. criar pastas `catalogs/` e `data/` por `profile`
4. carregar catalogos iniciais dos tres `profiles`
5. configurar wrappers de `prepare` e `finalize`
6. validar um ciclo completo em `feminino`
7. repetir validacao em `mae-e-bebe`
8. repetir validacao em `auto-e-moto`
9. confirmar que o unico parametro variavel e `profile`

## Checklist de validacao por rodada

1. catalogo do `profile` existe no `n8n`
2. `prepare` executou sem erro
3. `review_queue.json` foi gerado
4. revisao ficou sem itens pendentes
5. `finalize` executou sem erro
6. `dispatch_artifact.json` existe
7. `dispatch_report.json` existe
8. nenhuma etapa assumiu envio real

## O que ainda nao faz parte desta implantacao

Ainda fica fora do escopo desta fase:

- publisher real de `WhatsApp`
- integracao real de sessao ou provedor de envio
- confirmacao externa de entrega
- `ENABLE_REAL_PUBLISH=true`

## Evidencia de validacao

Este runbook ja possui uma validacao local registrada para o bloco atual:

- `validate_catalog.ps1`: validado
- `invoke_prepare.ps1`: validado
- `invoke_finalize.ps1`: validado
- dispatch bloqueado por `quiet_period`: validado
- dispatch liberado por horario forcado: validado

Detalhes e resultados numericos estao em
[`docs/n8n-validation.md`](n8n-validation.md).

## Proximo bloco apos este runbook

Depois que este runbook estiver implantado e validado no `n8n`, o proximo bloco
recomendado e:

1. criar a interface de `WhatsAppPublisher`
2. plugar essa interface ao `dispatch_execute_cli`
3. manter fallback em `dry-run`
4. registrar retorno auditavel por mensagem

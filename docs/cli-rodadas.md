# Chamadas CLI das Rodadas

Este documento registra como rodar o fluxo local por CLI, quais flags usar e
quais arquivos entram e saem em cada chamada.

## Quando usar cada comando

O ponto de entrada recomendado e `ofertas_bot.local_flow_cli`:

- `--stage prepare` gera a rodada e o pacote padrao de artefatos;
- `--stage finalize` consolida fila aprovada, manifesto e artefatos locais.

O `harness` permanece como ferramenta interna para teste e debug, quando for
necessario controlar artefatos individuais com flags `--save-*`.

## Comando operacional

Os tres nichos usam o mesmo comando. Somente o valor de `--profile` muda:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --profile mae-e-bebe
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --profile feminino
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --profile auto-e-moto
```

O profile resolve automaticamente marketplace, catalogo, destino, limite e
politica de selecao. A operacao normal nao precisa repetir `--niche`,
`--marketplace`, `--catalog-file`, `--target`, `--limit` ou flags `--save-*`.

Os artefatos ficam separados por profile:

```text
.data/<profile>/offers.json
.data/<profile>/selection_state.json
.data/<profile>/copy_briefs.json
.data/<profile>/messages.json
.data/<profile>/messages.txt
.data/<profile>/messages_preview.html
```

## Flags do harness

As flags operacionais mais importantes sao:

- `--niche`: nome logico do nicho da rodada;
- `--marketplace`: marketplace de referencia (`shopee`, `amazon`, `mock`);
- `--limit`: quantidade maxima de ofertas carregadas na rodada;
- `--target`: nome logico do destino;
- `--catalog-file`: arquivo local usado como entrada do collector;
- `--save-copy-briefs-json`: salva o contrato estruturado entre scorer e copy;
- `--save-messages-json`: salva as mensagens aprovadas em JSON;
- `--save-messages-text`: salva as mensagens aprovadas em TXT;
- `--save-messages-preview-html`: salva o preview visual da rodada.
- `--selection-state-json`: le e grava o estado operacional com `selected_at`,
  `cooldown_until`, `last_sent_at` e `selection_count`.

Flags auxiliares que continuam disponiveis:

- `--profile`
- `--subgroup`
- `--profiles-file`
- `--save-json`
- `--save-inspection-json`
- `--save-review-queue-json`
- `--print-provider-request`
- `--diagnose-real-http`
- `--execute-real-http-once`

## Arquivos de entrada

Os arquivos de entrada mais comuns para rodadas com catalogo curado sao:

- `catalogs\clean\feminino\clean_catalog_rating_4_8_plus.csv`
- `catalogs\clean\mae-e-bebe\clean_catalog_rating_4_8_plus.csv`
- `catalogs\clean\auto-e-moto\clean_catalog_rating_4_8_plus.csv`

Os caminhos estao registrados em `config/discovery_profiles.toml`. A flag
`--catalog-file` fica reservada para sobrescrita em teste ou debug.

## Arquivos de saida

### Saida manual via harness

Voce escolhe explicitamente os caminhos com flags `--save-*`.

Exemplo:

- `tmp\feminino-copy-briefs-default.json`
- `tmp\feminino-messages.json`
- `tmp\feminino-messages.txt`
- `tmp\feminino-messages-preview.html`

### Saida padrao via local_flow_cli

O `prepare` grava por padrao em `.data/<profile>/`:

- `.data/<profile>/offers.json`
- `.data/<profile>/selection_state.json`
- `.data/<profile>/copy_briefs.json`
- `.data/<profile>/messages.json`
- `.data/<profile>/messages.txt`
- `.data/<profile>/messages_preview.html`
- `.data/<profile>/review_queue.json`
- `.data/<profile>/review_plan.json`
- `.data/<profile>/review_plan.txt`

## Comandos do local_flow_cli

### Prepare padrao

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --profile feminino
```

### Finalize padrao

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize --profile feminino
```

## Contrato horizontal

`mae-e-bebe`, `feminino` e `auto-e-moto` passam pelo mesmo Collector, Scorer,
selecao, refresh, template, compliance e render HTML.

As diferencas de negocio ficam somente em config:

- `config/discovery_profiles.toml`: entrada e contexto da rodada;
- `config/selection_profiles.toml`: bandas de 20 itens, cooldown padrao e teto de 4 sem venda;
- `config/group_profiles.toml`: roteamento.

Quando uma capacidade compartilhada evoluir, os tres profiles devem ser
atualizados e testados no mesmo bloco.

## Validacao minima recomendada

Depois de qualquer ajuste em CLI, template, compliance ou render:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

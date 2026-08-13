# Discovery Shopee ate o Catalogo Supabase

Este documento descreve apenas o fluxo de `discovery` de novos itens Shopee
ate a chegada desses itens ao catalogo no Supabase.

Ele nao cobre:

- refresh comercial por `itemId`;
- ranking operacional;
- n8n;
- copy;
- publicacao;
- `publication_events`.

## Leitura geral

Hoje, o projeto ja possui pecas reutilizaveis para:

- definir perfis de discovery;
- coletar itens Shopee por `profile`;
- aplicar filtros iniciais;
- limpar e classificar catalogos;
- importar catalogo curado para o Supabase.

Mas o fluxo completo ainda nao esta automatizado ponta a ponta em um unico
orquestrador. Em varios pontos, o trigger continua sendo externo, normalmente o
operador.

## Fluxo atual

```text
[1] Definir profile de discovery
    -> [2] Rodar discovery Shopee
    -> [3] Aplicar filtros iniciais
    -> [4] Gerar massa local de itens coletados
    -> [5] Limpeza e curadoria do catalogo
    -> [6] Classificacao semantica
    -> [7] Gerar catalogo curado local
    -> [8] Validar contrato do catalogo
    -> [9] Importar para Supabase
    -> [10] Catalogo persistente no Supabase
```

## Etapas detalhadas

### [1] Definir profile de discovery

Arquivo principal:

```text
config/discovery_profiles.toml
```

O profile concentra a entrada operacional do nicho:

- `slug`
- `niche`
- `marketplace`
- `query`
- `keywords`
- `include_terms`
- `exclude_terms`
- `subgroups`
- `catalog_file`

Status da etapa:

- `manual`
- exige decisao externa do operador
- depois de salvo, o codigo ja consome o profile automaticamente

### [2] Rodar discovery Shopee

Bloco principal:

- `CollectorAgent`
- provider Shopee
- metodo `descobridor-geral`, quando configurado

Referencias:

- `src/ofertas_bot/agents/collector.py`
- `src/ofertas_bot/discovery_profiles.py`
- `docs/descobridor-geral.md`

O que acontece:

- o profile e carregado;
- o collector resolve o metodo de discovery;
- a busca Shopee roda por `profile`;
- a resposta bruta e normalizada.

Status da etapa:

- `semi-automatizada`
- o bloco interno ja existe e esta conectado
- ainda depende de trigger externo para iniciar a rodada

### [3] Aplicar filtros iniciais

Filtros iniciais do proprio profile:

- `include_terms`
- `exclude_terms`
- deduplicacao basica de ofertas

Referencia:

- `src/ofertas_bot/discovery_profiles.py`

O que acontece:

- o Collector coleta os itens;
- o profile reaplica filtros textuais;
- itens fora do escopo do nicho sao removidos.

Status da etapa:

- `automatizada dentro da coleta`
- nao e um passo manual separado
- ao disparar a coleta, essa filtragem ja roda junto

### [4] Gerar massa local de itens coletados

Saidas possiveis:

- resposta bruta do provider;
- itens normalizados;
- artefatos de inspecao, quando solicitados.

O que acontece:

- o collector devolve `offers` normalizadas;
- tambem pode devolver `raw_response`;
- ferramentas de inspecao podem salvar isso localmente.

Status da etapa:

- `semi-automatizada`
- a geracao da massa acontece no mesmo bloco da coleta
- a persistencia em arquivo depende do comando usado na rodada

### [5] Limpeza e curadoria do catalogo

Bloco principal:

- `docs/catalog-cleaning/catalog_cleaning_harness_v2.py`

O que acontece:

- valida contrato minimo de colunas;
- remove itens invalidos;
- remove duplicados;
- preserva rastreabilidade da limpeza.

Status da etapa:

- `automatizada como bloco proprio`
- nao esta encadeada automaticamente com a coleta anterior
- normalmente precisa de trigger externo do operador

### [6] Classificacao semantica

Bloco principal:

- taxonomia por `profile`
- mapeamento de `source_hits`
- fallback controlado por `productName`

Referencia:

- `docs/catalog-cleaning/catalog_cleaning_harness_v2.py`

O que acontece:

- `source_hits` conhecidos viram `subniches`;
- quando a origem e generica, o nome do produto pode ser usado como fallback;
- casos sem regra ficam registrados para revisao.

Status da etapa:

- `automatizada dentro da curadoria`
- nao costuma exigir trigger separado
- roda junto com a limpeza no harness atual

### [7] Gerar catalogo curado local

Saidas esperadas:

- `catalogs/processed/<profile>/...`
- `catalogs/clean/<profile>/clean_catalog_rating_4_8_plus.csv`

O que acontece:

- o harness gera os artefatos processados;
- o resultado curado local vira a base pronta para importacao.

Status da etapa:

- `automatizada como saida da curadoria`
- depende da execucao da etapa anterior
- a promocao do arquivo curado para o catalogo operacional ainda precisa de
  controle do operador

### [8] Validar contrato do catalogo

Blocos principais:

- `scripts/supabase/validate_catalog_schema.py`
- validacoes do contrato de importacao

O que acontece:

- verifica consistencia do catalogo;
- checa campos obrigatorios;
- checa `subniches`;
- ajuda a impedir importacao errada.

Status da etapa:

- `automatizada como script`
- ainda depende de trigger externo do operador

### [9] Importar para Supabase

Bloco principal:

- `scripts/supabase/import_catalog.py`

O que acontece:

- cria registro em `catalog_imports`;
- exige o instante explicito `observed_at` da coleta;
- identifica existencia por `profile + marketplace + item_id`;
- se o item ja existe, preserva seu cadastro e cria um `offer_snapshot`;
- se o item e novo, grava em `catalog_items` e cria o snapshot inicial;
- usa `profile + marketplace + source_sha256 + observed_at` como chave de
  idempotencia.

Um item que nao aparece em uma rodada posterior permanece em `catalog_items`.
Remocao ou desativacao depende de outra regra de negocio e nao faz parte do
discovery.

Status da etapa:

- `automatizada como bloco`
- nao esta ligada automaticamente ao fim da curadoria
- hoje costuma depender de trigger externo do operador

### [10] Catalogo persistente no Supabase

Destino principal:

- `offers.catalog_items`

O que acontece:

- os novos itens passam a existir no catalogo do Supabase;
- itens ja conhecidos ganham um novo snapshot comercial;
- ficam disponiveis para consumo pelas camadas seguintes do sistema.

Status da etapa:

- `resultado automatizado da importacao`
- depende de a etapa de importacao ter sido disparada

## O que ja esta conectado no codigo

Hoje, os encadeamentos mais claros sao estes:

### Bloco A: discovery bruto

```text
profile -> collector -> provider Shopee -> filtros iniciais -> lote normalizado
```

Esse bloco ja existe em codigo e roda de forma coesa.

### Bloco B: curadoria semantica

```text
catalogo bruto -> limpeza -> deduplicacao -> classificacao -> catalogo curado local
```

Esse bloco tambem ja existe e roda dentro do harness de limpeza.

### Bloco C: entrada no Supabase

```text
catalogo curado + observed_at
  -> validacao
  -> importacao idempotente
  -> item existente: offer_snapshots
  -> item novo: catalog_items + offer_snapshots
```

Esse bloco tambem ja possui scripts prontos.

## O que ainda nao esta orquestrado ponta a ponta

O que ainda falta como automacao unica e o encadeamento entre os blocos:

```text
discovery bruto
  -> curadoria
  -> validacao
  -> importacao Supabase
```

Hoje, essa passagem entre blocos ainda depende de trigger externo do operador.

## Resumo operacional

Leitura curta do estado atual:

- o projeto ja tem automacao interna dentro de varias etapas;
- o discovery nao esta "todo manual";
- o que ainda nao existe e um unico fluxo automatico fechado do discovery
  Shopee ate o catalogo Supabase;
- na pratica, hoje o operador ainda coordena a transicao entre os blocos.

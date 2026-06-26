# Catalogo Shopee

Este documento define como organizar a construcao de catalogo de produtos da
Shopee para nicho e subnicho, pensando no fluxo futuro com `n8n`.

Importante: esse processo de construcao de catalogo nao faz parte do pipeline
automatizado principal de ofertas e mensagens. Ele e uma etapa separada de
descoberta e curadoria.

## Objetivo

Sair do modelo de tentativa unica por query e passar para um modelo de
construcao progressiva de catalogo:

1. registrar `matchId` de referencia, quando existir;
2. coletar com chamadas por `keyword`;
3. complementar com chamadas por `shopId` ou por listas de lojas conhecidas;
4. fazer merge dos retornos;
5. remover itens por lista de termos negativos;
6. classificar o resultado em nicho e subnicho;
7. no futuro, confrontar o catalogo com os `matchId` registrados.

Decisao operacional atual:

- a geracao desse catalogo fica fora do processo automatizado principal;
- depois da descoberta, os itens ainda podem exigir revisao, porque preco,
  prazo, comissao e score efetivo podem mudar;
- por isso, o catalogo deve ser tratado como insumo curado para o fluxo
  `Collector -> Scorer -> Copywriter -> Compliance -> Publisher`, e nao como
  etapa automatica diaria desse mesmo pipeline.

## Regra de chamada

Para este fluxo, os parametros usados devem ser sempre tratados pelo nome da
API:

- `keyword`
- `shopId`
- `page`
- `limit`
- `listType`
- `sortType`
- `isAMSOffer`
- `isKeySeller`

Nada deve ser inventado fora do pedido ou da configuracao salva.

## Comportamento observado de `keyword`

Nas validacoes praticas feitas ate aqui, quando `productOfferV2(keyword: ...)`
recebe expressoes com mais de uma palavra, o comportamento aparente da busca e
de combinacao mais restritiva entre os termos.

Como isso nao esta documentado formalmente no contrato da API, a regra
operacional do projeto passa a ser:

- tratar esse comportamento como observacao pratica, nao como garantia oficial;
- evitar depender de uma unica chamada com varias palavras em `keyword`;
- executar uma chamada separada para cada item de `keyword_terms`;
- fazer o merge depois, dentro do projeto.

Exemplo:

- em vez de depender apenas de `keyword = "mae bebe fralda enxoval maternidade"`
- executar chamadas separadas para:
  - `keyword = "mae e bebe"`
  - `keyword = "bebe"`
  - `keyword = "maternidade"`
  - `keyword = "enxoval"`
  - `keyword = "fralda"`

## Arquivo versionado

O arquivo versionado de semente do catalogo e:

```text
config/shopee_catalog_profiles.toml
```

Ele guarda apenas a intencao operacional e os insumos de busca:

- `start_match_ids`
- `keyword_terms`
- `negative_terms`
- `shop_ids`
- `shop_names`
- `subniches`

Esses dados sao estaveis, editaveis e bons para versionamento.

## Estrutura recomendada

Cada profile deve ser organizado assim:

```toml
[[profiles]]
slug = "mae-e-bebe"
name = "Mae e Bebe"
start_match_ids = [100632]
keyword_terms = ["mae e bebe", "bebe", "maternidade"]
negative_terms = ["pet", "cachorro", "gato"]
shop_ids = []
shop_names = []
subniches = [
  { slug = "fraldas", name = "Fraldas", keyword_terms = ["fralda"], negative_terms = [] }
]
```

Leitura dos campos:

- `start_match_ids`: lista de referencia registrada no config. No estado atual,
  o builder nao faz query por `matchId`; esse campo fica reservado para
  confronto e filtro posterior do catalogo
- `keyword_terms`: chamadas adicionais por `productOfferV2(keyword: ...)`, uma
  query por termo
- `negative_terms`: termos que eliminam item do catalogo consolidado
- `shop_ids`: chamadas adicionais por `productOfferV2(shopId: ...)`
- `shop_names`: lista manual de lojas de referencia, para futura resolucao
- `subniches`: regras de classificacao posteriores ao merge

## Fluxo de merge

O fluxo de merge deve funcionar assim:

1. registrar os `matchId` de referencia no profile
2. coletar itens vindos de `keyword`, uma chamada por termo
3. coletar itens vindos de `shopId`
4. juntar tudo por chave unica `shopId:itemId`
5. salvar o conjunto bruto (`raw`)
6. remover duplicados
7. salvar o conjunto deduplicado
8. remover item quando qualquer `negative_term` aparecer no titulo ou outros
   campos textuais usados na classificacao
9. salvar o conjunto limpo (`clean`)
10. marcar origem de cada item:
   - veio de `keyword`
   - veio de `shopId`
   - veio de mais de uma origem
11. deixar o confronto com `matchId` como etapa posterior de validacao

## Persistencia pensada para n8n

Como o `n8n` ja esta definido como orquestrador, a regra recomendada e:

- o `n8n` dispara o job com `profile_slug` e `run_id`
- o codigo local executa a regra de negocio
- o `n8n` nao decide merge, filtro negativo ou classificacao

O que deve ficar versionado:

- `config/shopee_catalog_profiles.toml`
- codigo de merge
- codigo de classificacao
- documentacao do contrato

O que deve ficar como artefato de execucao, fora do Git:

```text
.data/shopee_catalog/<profile_slug>/<run_id>/
```

Sugestao de estrutura:

```text
.data/shopee_catalog/mae-e-bebe/2026-06-25T15-30-00Z/
  raw_catalog.csv
  raw_catalog.json
  deduplicated_catalog.csv
  deduplicated_catalog.json
  clean_catalog.csv
  clean_catalog.json
  run_summary.json
```

Leitura desses arquivos:

- `raw_catalog.*`: todas as linhas coletadas, incluindo repeticoes entre
  `keyword` e `shopId`
- `deduplicated_catalog.*`: merge por `shopId:itemId`, sem remover ainda por
  `negative_terms`
- `clean_catalog.*`: catalogo final, sem duplicacoes e sem itens bloqueados por
  `negative_terms`

Campos importantes nos artefatos:

- `source_type`: tipo da origem da linha coletada. No estado atual, os valores
  esperados sao `keyword` e `shopId`
- `source_value`: valor usado na origem daquela linha, por exemplo a palavra da
  busca ou o `shopId`
- `source_hits`: lista consolidada das origens que trouxeram o mesmo
  `shopId:itemId` depois do merge. No estado atual, esse campo nao registra
  `matchId`, porque o builder nao faz mais coleta por `matchId`

Regra atual de `matchId`:

- `start_match_ids` continua existindo no config
- o builder nao executa query por `matchId`
- esses valores aparecem apenas como referencia em `run_summary.json` e no log
  `INFO | reference_match_ids=...`
- o uso planejado de `matchId` passa a ser confronto posterior para validar ou
  negar itens fora da referencia esperada

## Logs de execucao

Executores longos desse fluxo devem escrever progresso no terminal.

Padrao atual:

- `INFO | profile=...`
- `INFO | run_id=...`
- `INFO | output_dir=...`
- `INFO | reference_match_ids=...`
- `INFO | source_start type=<source_type> value=<source_value>`
- `INFO | source=<source_type>:<source_value> page=<page> node_count=<n> hasNextPage=<bool>`
- `INFO | source_done type=<source_type> value=<source_value> rows=<n> unique=<n> pages=<n> stop=<reason>`
- `INFO | checkpoint raw=<n> deduplicated=<n> clean=<n>`

Esse log existe para que a equipe acompanhe a rodada em tempo real no terminal
e identifique rapidamente fonte travada, pagina vazia, volume inesperado ou
progresso lento.

## Tabelas logicas recomendadas

Se o projeto migrar de arquivo local para banco, a organizacao minima deve ser:

- `shopee_catalog_profiles`
- `shopee_catalog_profile_keywords`
- `shopee_catalog_profile_negative_terms`
- `shopee_catalog_profile_shops`
- `shopee_catalog_runs`
- `shopee_catalog_run_items`
- `shopee_catalog_run_item_sources`

Assim o `n8n` consegue:

- disparar execucao
- acompanhar status
- consumir resumo
- enviar o resultado para proxima etapa

sem carregar a regra central.

## Decisao operacional atual

Para construcao de catalogo Shopee:

- `config/discovery_profiles.toml` continua util para descoberta e fluxo atual;
- `config/shopee_catalog_profiles.toml` passa a ser a fonte de verdade para a
  futura construcao de catalogo por `keyword`, `shopId` e termos negativos,
  mantendo `matchId` apenas como referencia registrada no profile;
- o executor deve produzir sempre artefatos `raw`, `deduplicated` e `clean`,
  orientados a `n8n`.

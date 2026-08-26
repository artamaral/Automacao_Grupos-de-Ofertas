# Limpeza de taxonomia do catálogo Feminino e lacuna no pipeline atual

## Objetivo

Este documento registra a limpeza de taxonomia realizada sobre o catálogo `feminino` e documenta uma lacuna estrutural do pipeline atual: a taxonomia granular oficial existe no repositório, mas não está sendo aplicada automaticamente na geração do `clean_catalog.csv` que segue para importação no Supabase.

## Diagnóstico do pipeline atual

A taxonomia granular oficial de `feminino` continua versionada no repositório em:

`config/catalog-taxonomies/feminino/shopee_feminino_subniches_taxonomia_base.json`

Ela define uma taxonomia fechada com slugs granulares como, entre outros:

- `moda-calcas`
- `moda-partes-de-cima`
- `moda-saias-e-shorts`
- `moda-vestidos`
- `moda-fitness`
- `moda-praia`
- `skincare-facial`
- `cabelo-tratamento`
- `cabelo-ferramentas`
- `maquiagem-pele`
- `maquiagem-olhos`
- `maquiagem-labios`
- `maquiagem-organizacao`
- `maquiagem-pinceis-e-esponjas`
- `unhas-manicure`
- `lingerie-e-intimos`
- `bolsas-e-carteiras`
- `acessorios-femininos`

O problema não é perda ou remoção da taxonomia. O problema é que o fluxo atual do builder não carrega esse arquivo para produzir a classificação granular final.

Hoje o builder usa os subnichos macro do perfil em `config/shopee_catalog_profiles.toml`, resultando em categorias amplas como:

- `moda`
- `maquiagem`
- `cabelo`
- `skincare`
- `unhas`
- `acessorios`

Historicamente, havia uma etapa posterior de limpeza/classificação que aplicava a taxonomia granular ao catálogo já descoberto. Na arquitetura atual, o caminho ficou essencialmente:

```text
Shopee discovery
  -> builder
  -> clean_catalog.csv com macros
  -> import_catalog.py
  -> Supabase
```

O fluxo desejado é:

```text
Shopee discovery
  -> builder
  -> taxonomia granular oficial
  -> filtros de qualidade
  -> CSV final e import-ready
  -> import_catalog.py
  -> Supabase
```

Portanto, o que foi perdido no fluxo foi a ligação automática do harness/taxonomia granular entre o builder e o importador.

## Limpeza executada sobre o catálogo atual

O arquivo de trabalho tinha inicialmente 30.424 linhas.

### Filtro de qualidade

Foi aplicado o requisito de qualidade já adotado pelo importador:

- `ratingStar >= 4.8`

Após esse filtro, restaram 22.762 itens.

### Limitação importante do arquivo atual

O `clean_catalog.csv` atual não possui mais `source_hits`.

Isso impede reproduzir integralmente o comportamento histórico do harness, porque a taxonomia original priorizava o mapeamento da palavra-chave de origem (`source keyword -> subniche`).

Diante disso, a limpeza foi feita a partir de `productName`, usando como base as `fallback_product_name_rules` já existentes na taxonomia oficial e refinamentos explícitos aprovados durante a revisão.

Nenhum novo sub-subnicho foi criado.

## Tratamento de `feminino-geral`

A primeira aplicação da taxonomia granular deixou 3.508 itens em `feminino-geral`.

Foram realizadas passagens adicionais para reduzir esse fallback sem forçar classificações inseguras. Os itens foram redistribuídos apenas para slugs já existentes quando havia evidência textual suficiente.

Os casos ainda ambíguos foram mantidos como `feminino-geral`.

Na versão final preparada para Supabase, restaram 1.199 itens em `feminino-geral`.

## Regras e decisões registradas durante a revisão

### Unhas

- `esmalte` -> `unhas-manicure`

### Organização de maquiagem

- `necessaire` / `nécessaire` -> `maquiagem-organizacao`

### Moda - partes de cima

Itens como blusa, blusinha, camiseta, t-shirt, regata, cropped, body, camisa e top podem ser classificados em:

- `moda-partes-de-cima`

### Moda - calças, saias e shorts

Para regras adicionais de recuperação:

- títulos com `kit` podem ser classificados em `moda-calcas` ou `moda-saias-e-shorts` conforme o produto;
- quando o título contém part number/código de peça, a regra não deve classificar automaticamente o item apenas pelo nome do produto.

Exemplos de tokens tratados como part number:

- `ADD8942`
- `AS1401`
- `YY20340`
- `H980`

### Lingerie e íntimos

Termos aprovados para `lingerie-e-intimos`:

- `hobby`
- `camisola`
- `meia de renda`
- `espartilho`

Termos de compressão não devem ser classificados automaticamente como lingerie.

### Chapinha

A palavra `chapinha` é ambígua.

Ela pode significar ferramenta de cabelo, mas também pequenas chapas/ferragens usadas em móveis, pés de sofá, cadeiras, cordões e estruturas similares.

Regra desejada:

- `chapinha` com contexto de cabelo -> `cabelo-ferramentas`;
- `chapinha` com contexto claro de ferragem/móveis -> remover do perfil `feminino`.

Foram identificados e removidos 35 falsos positivos desse tipo na revisão final.

Exemplos de falsos positivos:

- chapinhas dentadas/garra para cordão;
- chapinhas para pés de sofá;
- chapinhas para pés palito;
- chapinhas para móveis, mesas e cadeiras.

## Falsos positivos fora do nicho

Além de erros por `chapinha`, foram encontrados produtos claramente fora do nicho feminino, como guarda-roupas, móveis e acessórios de mobiliário.

Esses produtos não devem receber um subnicho artificial. Quando a evidência mostra que o item está fora do perfil `feminino`, a ação correta é removê-lo do catálogo desse perfil.

## Artefato final produzido

A versão final limpa preparada para importação ficou com:

- 22.564 itens;
- 0 `itemId` inválido;
- 0 `itemId` duplicado;
- 0 item com `ratingStar < 4.8`;
- 0 rating inválido;
- 0 `subniches` vazio;
- 0 `subniches` com JSON inválido;
- 1.199 itens ainda em `feminino-geral`.

O objetivo desta versão foi preservar apenas classificações verificáveis, evitando forçar itens ambíguos para sub-subnichos incorretos.

## Problema estrutural a corrigir

A limpeza realizada manualmente não deve virar uma rotina operacional manual.

O pipeline precisa voltar a aplicar automaticamente a taxonomia granular oficial antes de produzir o CSV import-ready.

A correção estrutural deve garantir que:

1. o builder faça discovery e deduplicação;
2. a taxonomia oficial de `feminino` seja carregada automaticamente;
3. `source_hits`, quando disponíveis, sejam preservados até a etapa de taxonomia;
4. a classificação por palavra-chave de origem volte a ser a primeira base de classificação;
5. as `fallback_product_name_rules` sejam usadas apenas quando necessário;
6. os refinamentos aprovados nesta revisão sejam incorporados à lógica oficial, sempre apontando para sub-subnichos já existentes;
7. falsos positivos claros sejam removidos do perfil;
8. os filtros de qualidade sejam aplicados antes da importação;
9. o artefato final tenha significado único: catálogo limpo, granularmente taxonomizado e pronto para `import_catalog.py`.

## Contrato desejado para `clean_catalog.csv`

`clean_catalog.csv` não deve representar um intermediário com categorias macro.

Ele deve representar o artefato final do catálogo curado, com:

- qualidade mínima satisfeita;
- itemId único;
- taxonomia granular aplicada;
- subniche não vazio;
- falsos positivos removidos;
- formato compatível com `scripts/supabase/import_catalog.py`.

## Próxima implementação recomendada

Restaurar a etapa automática de taxonomia no pipeline e criar testes que falhem caso o catálogo de `feminino` chegue ao importador apenas com os macros definidos em `shopee_catalog_profiles.toml`.

A implementação deve reutilizar a taxonomia oficial versionada no repositório, em vez de duplicar regras em um novo classificador independente.

## Registro operacional: calcados feminino 2026-08-25

Esta rodada documenta a primeira carga incremental do discovery scope `calcado`
para o profile operacional `feminino`.

### Decisao de taxonomia

Durante a avaliacao dos dados descobertos, foram aprovados estes ajustes na
taxonomia oficial de `feminino`:

- `tamanco` -> `calcados-sandalia`;
- `papete` -> `calcados-sandalia`;
- `rasteira` -> `calcados-rasteirinha`.

Os termos `slide`, `loafer` e `birken` permaneceram sem mapeamento aprovado
para importacao automatica nesta rodada. Quando aparecerem apenas por keyword
de discovery e nao houver outra regra taxonomica granular, devem ser descartados
ou revisados antes de entrar no catalogo ativo.

### Limpeza aplicada

Entrada do discovery:

```powershell
.data\shopee_catalog\feminino\scopes\calcado\calcado-2026-08-26\deduplicated_catalog.csv
```

Comando de limpeza executado:

```powershell
.\.venv\Scripts\python.exe docs\catalog-cleaning\catalog_cleaning_harness_v2.py `
  --input .data\shopee_catalog\feminino\scopes\calcado\calcado-2026-08-26\deduplicated_catalog.csv `
  --outdir catalogs\processed\feminino\calcado-2026-08-26 `
  --taxonomy-file config\catalog-taxonomies\feminino\shopee_feminino_subniches_taxonomia_base.json
```

Resumo do harness apos a atualizacao da taxonomia:

- linhas originais: 1.656;
- removidas por qualidade: 740;
- removidas por termo proibido: 223;
- catalogo limpo: 693;
- grupos duplicados por nome/preco: 14;
- candidatos duplicados marcados: 15;
- keywords de origem ainda sem mapeamento: `loafer`, `slide`.

Distribuicao de subnichos no catalogo limpo:

- `calcados-sandalia`: 428;
- `calcados-chinelo`: 334;
- `feminino-geral`: 107;
- `calcados-rasteirinha`: 105;
- `calcados-sapatilha`: 49;
- `calcados-mocassim`: 25.

### Artefato importado no Supabase

Antes da importacao remota foi gerado o CSV final:

```powershell
catalogs\processed\feminino\calcado-2026-08-26\shopee_catalogo_limpo_subniches_import_supabase.csv
```

Esse arquivo manteve somente itens dos cinco subnichos de calcados aprovados,
com `ratingStar >= 4.8` e sem duplicados marcados como nao-keeper.

Resultado da preparacao:

- entrada limpa: 693 linhas;
- import-ready: 520 linhas;
- descartadas por `feminino-geral` ou subnicho inesperado: 107;
- descartadas por rating abaixo de 4.8 ou invalido: 52;
- descartadas por duplicidade nao-keeper: 14.

A validacao dry-run do importador retornou:

```text
VALIDATION=OK profile=feminino rows=520 rating=4.8-5.0 subniches=5 sha256=c63637ee391c...
REMOTE_WRITE=SKIPPED
```

### Resultado da carga remota

A carga foi aplicada com `observed_at=2026-08-25T21:31:17-03:00` e confirmacao
explicita `IMPORT_CURATED_CATALOG`.

Resultado confirmado:

- `catalog_imports.id`: `50b62530-d93b-4f51-985e-53610333d57a`;
- `profile_slug`: `feminino`;
- `marketplace`: `shopee`;
- `status`: `completed`;
- `row_count`: 520;
- novos itens: 519;
- itens ja existentes: 1;
- snapshots inseridos: 520.

A verificacao posterior no Supabase confirmou 520 snapshots associados ao
`catalog_import_id`.

Observacao: um item ja existente preservou o subnicho antigo `moda-praia` em
`catalog_items`, porque a importacao incremental nao reclassifica itens
existentes; ela registra o novo snapshot da oferta. O item foi
`45709883721`, uma sandalia romana feminina.

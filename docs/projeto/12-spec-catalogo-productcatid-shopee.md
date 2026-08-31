# 12 - Spec de Catalogo Shopee por ProductCatId

## Status

Decisoes de produto e operacao fechadas. A fundacao de discovery, limpeza,
schema, referencias, staging e cutover atomico no Supabase foi implementada e
validada. Permanecem pendentes o refresh real, o planejamento do proximo dia,
deploy VPS e validacao do n8n ativo.

## Implementacao realizada

- A matriz versionada vigente e
  `config/shopee_productcatid_quotas_feminino.csv`, com 46 categorias e 140
  itens por dia.
- O discovery em lote usa `productCatId` singular no request e registra o
  mesmo campo em cada linha do CSV bruto. `productCatIds` continua somente
  como dado bruto do response.
- O limpador `scripts/shopee/clean_productcatid_catalog.py` nao classifica
  subnichos: valida allowlist, item, preco, imagem, comissao, vendas, rating
  maior ou igual a 4.5 e os termos proibidos vigentes.
- A rodada validada teve 18.179 linhas brutas e produziu 4.511 itens limpos;
  nao houve conflito de um `itemId` entre categorias.
- A cobertura do catalogo limpo atende todas as 46 quotas e o total de 140.
- A migration remota `20260830172654_productcatid_catalog` foi aplicada ao
  projeto Supabase. Ela criou as tabelas de categorias e quotas, adicionou os
  campos de categoria/status ao catalogo e propagou `product_cat_id` ate
  `v_daily_dispatch_ready_tracked`, sem stale, refresh, fila ou cutover.
- A carga de referencia Supabase foi validada: 1.339 categorias oficiais,
  46 quotas ativas, soma 140, FK valida e RLS habilitado nas duas tabelas.
- A migration remota `productcatid_import_staging` criou uma area inerte de
  pre-corte, protegida por RLS e sem leitor operacional:
  `offers.productcatid_import_batches` e
  `offers.productcatid_import_batch_items`. Ela nao e um segundo catalogo e
  nao participa de ranking, refresh, planner, ready views ou n8n.
- O CLI `scripts/supabase/stage_productcatid_catalog.py` validou e carregou o
  lote `f766c367-26ff-4081-85ba-685b36180f9e`, geracao
  `productcatid-20260830`: 4.511 itens e 46 categorias, todos dentro da
  matriz ativa. A verificacao posterior confirmou RLS nas duas tabelas e zero
  linha dessa geracao em `offers.catalog_items`; portanto nao houve alteracao
  de `current`, `legacy`, snapshots, fila ou freshness.
- Ranking, refresh e planner foram preparados localmente para o modo explicito
  de `productCatId`. A ativacao ocorreu apenas durante o cutover atomico,
  depois da confirmacao das 21h BRT, sem modificar o plano confirmado do dia.

## Etapa concluida - Cutover atomico ProductCatId

### Execucao

- Migration remota `productcatid_ranking_refresh_planner` aplicada apos
  autorizacao explicita. Ela executou preflight, migration de views e promocao
  do staging em uma unica transacao do Supabase.
- O preflight exigiu: horario posterior a 21h BRT, lote com 4.511 itens e 46
  categorias, rating minimo 4,5, cobertura da matriz, ausencia de conflito de
  `stable_key` e as 140 linhas do plano do dia em `confirmed`.
- O lote `f766c367-26ff-4081-85ba-685b36180f9e` foi promovido como geracao
  `productcatid-20260830`; os itens femininos anteriores foram preservados
  como `legacy`, sem hard delete.
- `refresh_required_after` foi preenchido nos 4.511 itens `current`. Logo,
  nenhum snapshot anterior ao corte pode ser reutilizado como `FRESH` pelo
  ranking, planner ou ready view.

### Auditoria remota apos commit

| Verificacao | Resultado |
| --- | ---: |
| Itens `current` | 4.511 |
| Itens `legacy` | 23.935 |
| Categorias `current` | 46 |
| Itens current sem `product_cat_id` | 0 |
| Itens current com rating nulo ou menor que 4,5 | 0 |
| Linhas current reconciliadas com staging | 4.511 |
| Itens current com cutoff de refresh | 4.511 |
| Plano do dia | 140 `confirmed` |
| Registros de cutover | 1 |

### Proximo passo controlado

O refresh real foi executado em seguida por matriz `product_cat_id`: 140
chamadas Shopee, 140 sucessos, 140 snapshots e zero falhas ou `no_node`. A
validacao remota confirmou cobertura `FRESH` suficiente em todas as 46 quotas.

O planner do proximo dia ainda nao foi persistido. O dry-run para
`2026-08-31` foi corretamente bloqueado porque a regra operacional vigente
exige `last_checked_at` na mesma data do plano, enquanto o refresh ocorreu em
`2026-08-30` apos as 21h BRT. A decisao pendente e manter essa regra e executar
novo refresh apos meia-noite, ou alterar explicitamente a semantica de
freshness para TTL/cutoff. Nenhum plano parcial foi criado.

O cutover e refresh nao executaram tracking, deploy VPS, ativacao do n8n ou
envio real.

## Etapa concluida - Staging controlado pre-cutover

### Objetivo

Preparar no Supabase uma geracao validada do novo catalogo feminino para o
cutover, sem antecipar nenhuma mudanca no catalogo operacional. O staging e
um registro de importacao temporario e auditavel; ele nao representa um
segundo catalogo persistente nem uma segunda fonte operacional.

### Entradas

- Catalogo limpo:
  `.data/shopee_productcatid/clean/clean_catalog_productcatid_rating_4_5_plus.csv`.
- Matriz canonica:
  `config/shopee_productcatid_quotas_feminino.csv`, com 46 IDs e total 140.
- Taxonomia oficial local: `data/shopee_product_categories.csv`.
- Geracao declarada: `productcatid-20260830`.
- Momento observado em UTC, informado explicitamente no comando de escrita.

### Processo executado

1. O CLI `scripts/supabase/stage_productcatid_catalog.py` le o catalogo pelo
   mesmo contrato operacional de importacao, exigindo `productCatId` singular.
2. Ele valida rating minimo 4.5, IDs unicos, chave estavel unica, allowlist de
   categorias, presenca de todas as 46 categorias da matriz e compatibilidade
   da matriz com a taxonomia oficial local.
3. Sem `--apply`, o processo e somente dry-run. Com `--apply`, exige a
   confirmacao literal `STAGE_PRODUCTCATID_CATALOG`.
4. A escrita usa lock transacional por profile e marketplace e e idempotente
   por `profile + marketplace + catalog_generation`: uma reexecucao com a
   mesma fonte reutiliza o lote; uma fonte diferente para a mesma geracao e
   bloqueada.
5. A migration `productcatid_import_staging` criou
   `offers.productcatid_import_batches` e
   `offers.productcatid_import_batch_items`, ambas com RLS habilitado e sem
   privilegio para `public`, `anon` ou `authenticated`.

### Saida e evidencia

| Campo | Resultado |
| --- | --- |
| Geracao | `productcatid-20260830` |
| Batch Supabase | `f766c367-26ff-4081-85ba-685b36180f9e` |
| Itens em staging | 4.511 |
| Categorias em staging | 46 |
| Itens fora da matriz ativa | 0 |
| Itens com rating abaixo de 4.5 | 0 |
| Linhas dessa geracao em `offers.catalog_items` | 0 |

### Garantias desta etapa

- Nao inseriu, atualizou, promoveu ou tornou legacy qualquer linha de
  `offers.catalog_items`.
- Nao criou snapshots, nao marcou item stale e nao alterou freshness.
- Nao alterou `offers.daily_dispatch_plan`, ranking, refresh, ready views,
  tracking, n8n ou qualquer envio.
- A promocao para `current`, a segregacao do catalogo anterior e o stale
  continuam exclusivos do cutover apos 21h BRT.

### Validacoes automatizadas executadas

- `ruff check` do CLI e dos testes relacionados: aprovado.
- `pytest` de catalogo, migration, staging e importacao: `23 passed`.
- Dry-run real do CSV limpo: `PRODUCTCATID_STAGE_VALIDATION=OK`, 4.511 itens
  e 46 categorias.
- Consulta remota apos escrita: contagens reconciliadas, RLS nas duas tabelas
  de staging e nenhum registro operacional associado a essa geracao.

## Etapa preparada - Ranking, refresh e planner por ProductCatId

### Integracao implementada

- `DispatchCandidate`, a persistencia de `daily_dispatch_plan` e os snapshots
  de refresh agora carregam `product_cat_id` singular.
- O refresh preserva `productCatIds` do response apenas como dado bruto
  historico e grava `product_cat_id` a partir da categoria solicitada no
  catalogo, sem inferir categoria a partir da resposta.
- O refresh possui selecao explicita por matriz, sem fallback entre
  categorias. Cada categoria precisa oferecer exatamente sua quota; caso
  contrario a execucao e bloqueada antes de qualquer plano.
- O planner recebeu `plan_productcatid_dispatches` e o CLI
  `python -m ofertas_bot.tools.plan_daily_dispatch` recebeu
  `--productcatid-matrix <arquivo>`. Sem essa flag, o planner atual por
  subnicho permanece inalterado.
- O novo plano usa `selection_bucket='productcatid_exact'` e
  `selection_reason='productcatid:<id>'`. Quando a categoria nao tem
  candidatos aptos suficientes, o planner completa a lacuna com o melhor score
  geral ainda nao usado e registra
  `selection_reason='productcatid:<id>:top_score_fallback'`. O campo legado
  `primary_subniche` permanece apenas como rotulo tecnico de compatibilidade
  (`productcatid:<id>`), nao como classificacao interna.

### Migration aplicada durante o cutover atomico

`supabase/migrations/202608300003_productcatid_ranking_refresh_planner.sql`
prepara a view `offers.v_offer_ranking_productcatid_current`, que:

- le somente `catalog_status='current'` com `product_cat_id` preenchido;
- aplica elegibilidade de rating maior ou igual a 4.5;
- expoe `product_cat_id`, `is_productcatid_eligible` e
  `rank_product_cat`;
- mantem `security_invoker = true`;
- aceita o bucket `productcatid_exact` na fila persistida.

Ela foi aplicada na mesma transacao da promocao do staging. Assim, a view nao
ficou exposta em estado vazio entre a alteracao da regra e a promocao da
geracao `current`.

### Validacao automatizada

- Simulacao com a matriz real: 46 categorias, 140 candidatos, 140 slots e 10
  itens em cada uma das 14 janelas.
- Simulacao de cobertura incompleta: completa a lacuna com fallback geral por
  score quando houver candidato apto sobrando; falha apenas quando o universo
  elegivel nao fecha os 140 slots.
- Refresh por categoria: seleciona somente quotas exatas e falha quando uma
  categoria nao tem candidatos suficientes.

## Revisao da matriz por cobertura de candidatos

A matriz inicial tinha 53 categorias. Na primeira limpeza, seis categorias nao
tinham cobertura suficiente para suas quotas sob as travas obrigatorias de
rating maior ou igual a 4.5, vendas maiores que 1, comissao, imagem e termos
proibidos.

- `100365`: deficit de 2; os itens retornados falharam rating ou vendas.
- `100380`: deficit de 1; os itens retornados falharam rating ou vendas.
- `100387`, `100401`, `100402` e `100590`: nao tiveram candidatos limpos.

O usuario revisou `C:\Users\arthu\Downloads\Book1.xlsx`, aba `Sheet4`, e
removeu essas seis categorias. As quotas das 46 categorias restantes foram
redistribuidas na planilha, mantendo o total diario de 140. A matriz revisada
foi revalidada contra o mesmo CSV bruto: 4.511 candidatos limpos, nenhuma
quota descoberta em falta e nenhuma categoria fora da allowlist.

## Objetivo

Migrar o catalogo operacional Shopee do profile `feminino` para uma base
orientada pelo `productCatId` singular definido no request.

A taxonomia oficial da Shopee passa a ser a classificacao canonica. Nenhuma
taxonomia interna ou versao de taxonomia deve classificar os novos itens. A
lista de termos proibidos continua sendo o unico filtro semantico textual.

A mudanca deve afetar somente a forma como a categoria e lida, persistida e
usada pelo discovery, catalogo, ranking, refresh e planner. Os demais
comportamentos operacionais devem permanecer iguais.

Fluxo alvo:

```text
matriz feminina de 46 productCatId e quotas
  -> discovery productOfferV2(productCatId)
  -> limpeza com termos proibidos e rating >= 4.5
  -> catalogo feminino com productCatId singular
  -> catalog_items + shopee_product_categories + quotas no Supabase
  -> snapshots comerciais
  -> v_offer_ranking_current com productCatId
  -> planner de productCatId com 140 itens por dia
  -> daily_dispatch_plan com productCatId
  -> v_daily_dispatch_ready
  -> v_daily_dispatch_ready_tracked
  -> n8n
```

## Decisoes fechadas

### Identidade da categoria

- O unico campo de categoria operacional e `productCatId`, no singular.
- No CSV e nos contratos Python, o nome canonico e `productCatId`.
- No Supabase, o nome canonico e `product_cat_id`.
- O valor e sempre a categoria definida pela matriz feminina e enviada no
  request de discovery.
- `productCatIds`, com `s`, e um campo de response da Shopee e nao participa da
  classificacao, deduplicacao, persistencia operacional, ranking, refresh,
  planner ou fila.
- O campo plural pode continuar existindo em payload bruto ou coluna legada ja
  existente, mas nao deve ser lido como fonte de verdade nem ganhar novo
  consumidor.
- Nao existira `primaryProductCatId`, `primary_product_cat_id` nem logica para
  escolher um elemento de `productCatIds`.

### Profile e escopo

- Todos os itens descobertos a partir da matriz desta spec pertencem ao profile
  `feminino` e ao marketplace `shopee`.
- Essa regra vale apenas para este pipeline; outros profiles nao devem ser
  alterados.
- As 46 categorias desta spec sao a allowlist do novo catalogo feminino.
- Todos os 46 IDs existem em `data/shopee_product_categories.csv`.
- A soma das quotas e 140 itens por dia.

### Catalogo unico e status

- Existira um unico catalogo persistente em `offers.catalog_items`.
- A identidade continua sendo `profile + marketplace + item_id`.
- `catalog_status` tera os valores `current` e `legacy`.
- Um item existente no catalogo anterior e no novo catalogo permanece em uma
  unica linha e termina como `current`.
- Um item do catalogo anterior ausente do novo catalogo termina como `legacy`.
- Um item novo e inserido como `current`.
- Nenhum item e removido por hard delete.
- `catalog_generation` identifica a execucao ou cutover do catalogo e nao e
  uma versao de taxonomia.
- Antes de atualizar uma linha existente, seu estado anterior deve ser
  preservado no historico de importacao para permitir auditoria e rollback.

### Duplicidade entre categorias

- A matriz nao possui `productCatId` duplicado.
- O teste fornecido nao possui sobreposicao intencional de itens entre
  categorias.
- Se o mesmo `item_id` aparecer associado a mais de um `productCatId` durante
  discovery ou limpeza, a execucao deve falhar antes da importacao.
- O erro deve listar somente `item_id` e categorias conflitantes, sem escolher
  precedencia silenciosamente.
- A sobreposicao entre catalogo legacy e catalogo novo nao e conflito: a linha
  existente deve ser promovida para `current`.

### Planner e fila

- O planner de `productCatId` ja foi preparado pelo usuario e sera fornecido no
  inicio da implementacao.
- A implementacao deve integrar esse planner, sem inventar familias, niveis ou
  quotas diferentes.
- A quota diaria de cada categoria e a quantidade registrada nesta spec.
- O total diario permanece em 140 itens.
- A grade operacional atual permanece com 14 janelas, das 08h as 21h, e 10
  slots por janela.
- Horarios, sequenciamento, claim, tracking, cooldown e idempotencia existentes
  devem ser preservados.
- O plano deve conter somente itens `current`, elegiveis e `FRESH` no dia BRT.
- Se nao houver candidatos suficientes para cumprir uma quota, o planner deve
  preencher a lacuna com o melhor candidato geral apto ainda nao usado.
- Se nem o fallback geral tiver candidatos suficientes para fechar o total
  diario, o planner deve falhar sem persistir um plano parcial.
- O n8n continua apenas consumindo a fila pronta; ele nao classifica, ranqueia
  nem redistribui categorias.

### Rating e termos proibidos

- O piso de elegibilidade muda de `4.8` para `4.5`.
- `rating = 4.5` e aceito quando as demais travas forem satisfeitas.
- `rating < 4.5` ou rating nulo e inelegivel.
- O motivo canonico passa a ser `rating_below_4_5`.
- A lista atual de termos proibidos permanece obrigatoria.
- A normalizacao atual de acentos e caixa deve ser preservada.
- Nenhuma taxonomia interna deve ser usada para completar ou corrigir a
  classificacao Shopee.

### Cutover

- O cutover e a ultima etapa da implementacao.
- Deve acontecer depois das 21h em `America/Sao_Paulo`, quando a fila do dia ja
  terminou.
- O plano encerrado do dia nao deve ser substituido, reaberto ou apagado.
- O catalogo anterior deve ser marcado como `legacy`.
- A importacao do novo catalogo deve promover ou inserir seus itens como
  `current`.
- Itens legacy reencontrados no novo catalogo terminam como `current`.
- Depois do upsert, `refresh_required_after` deve forcar os itens `current` com
  snapshot anterior ao cutover para `STALE`.
- Itens sem snapshot permanecem `MISSING`; itens com snapshot anterior ao
  cutoff ficam `STALE`.
- O refresh real deve ocorrer antes da geracao do plano do dia seguinte.
- O plano seguinte so pode ser persistido quando todas as quotas puderem ser
  preenchidas com itens `FRESH`.
- Se importacao, refresh ou planner falhar, nao deve existir plano parcial. O
  estado anterior deve poder ser restaurado a partir do historico do cutover.

## Matriz canonica do feminino

Origem revisada: `C:\Users\arthu\Downloads\Book1.xlsx`, aba `Sheet4`, intervalo
`A1:B47`.

Na planilha recebida, a coluna B nao possui cabecalho. Para o contrato
versionado, ela deve ser normalizada como `daily_quantity`.

Validacoes da fonte:

- 46 categorias;
- 46 IDs unicos;
- nenhuma quantidade nula, zero ou negativa;
- todas as categorias existem em `data/shopee_product_categories.csv`;
- menor quota: 2;
- maior quota: 8;
- soma das quotas: 140.

| productCatId | daily_quantity |
| ---: | ---: |
| 100350 | 4 |
| 100351 | 4 |
| 100352 | 4 |
| 100353 | 2 |
| 100354 | 2 |
| 100355 | 2 |
| 100357 | 4 |
| 100358 | 8 |
| 100360 | 2 |
| 100361 | 2 |
| 100102 | 2 |
| 100103 | 3 |
| 100104 | 3 |
| 100363 | 2 |
| 100364 | 2 |
| 100381 | 3 |
| 100382 | 3 |
| 100389 | 2 |
| 100390 | 2 |
| 100391 | 2 |
| 100400 | 3 |
| 101615 | 3 |
| 102029 | 3 |
| 102030 | 3 |
| 102032 | 3 |
| 100869 | 5 |
| 100871 | 3 |
| 100872 | 2 |
| 100897 | 2 |
| 101669 | 2 |
| 101670 | 2 |
| 100901 | 3 |
| 100162 | 5 |
| 100091 | 3 |
| 100092 | 3 |
| 100093 | 3 |
| 100094 | 3 |
| 100095 | 2 |
| 100338 | 2 |
| 100586 | 2 |
| 100588 | 3 |
| 100589 | 4 |
| 100591 | 4 |
| 100559 | 3 |
| 100560 | 4 |
| 100593 | 5 |
| 100594 | 5 |
| **Total** | **140** |

Durante a implementacao, essa matriz deve ser copiada para um arquivo
versionado no repositorio, com cabecalho explicito, e tratada como configuracao
canonica do planner. O anexo em Downloads nao deve ser dependencia da VPS.

## O que deve ser alterado

### Discovery Shopee

Entradas:

- matriz versionada de `productCatId` do feminino;
- parametros explicitos da chamada Shopee;
- termos proibidos do profile;
- configuracao de paginacao e retry ja suportada pelo provider.

Saidas:

- CSV bruto com `productCatId` em todas as linhas;
- relatorio por categoria com paginas, nodes, `hasNextPage`, vazios e erros;
- registro de categoria mesmo quando a resposta vier vazia;
- relatorio de item associado a mais de uma categoria;
- nenhum segredo impresso.

Alteracoes obrigatorias:

- carregar os 46 IDs da matriz canonica;
- enviar cada ID como `productCatId` no request;
- preservar o ID solicitado em todas as linhas produzidas;
- validar `itemId` positivo;
- nao usar `productCatIds` do response;
- manter a assinatura GraphQL e o provider existentes;
- manter defaults somente quando aceitos explicitamente pela CLI ou
  configuracao vigente.

### Contrato de catalogo local

Entradas:

- CSV bruto por `productCatId`;
- termos proibidos;
- `ratingStar >= 4.5`;
- regras atuais de preco, link, imagem, comissao e vendas.

Saidas:

- `clean_catalog_productcatid_rating_4_5_plus.csv`;
- uma linha por `itemId` no profile;
- campo obrigatorio `productCatId`;
- relatorio de descartes com motivo;
- relatorio impeditivo de conflito entre categorias.

Alteracoes obrigatorias:

- incluir `productCatId` no contrato operacional;
- remover dependencia de classificacao e versao de taxonomia interna deste
  novo caminho;
- preservar apenas termos proibidos como filtro textual;
- trocar o contrato de rating e os motivos de `4.8` para `4.5`;
- rejeitar rating nulo;
- impedir importacao quando um item possuir duas categorias.

### Supabase - schema

Criar ou ampliar:

#### `offers.shopee_product_categories`

Tabela com a arvore oficial completa:

```text
category_id bigint primary key
category text
sub_category text
level_3 text
level_4 text
level_5 text
category_path text
source_sha256 text
loaded_at timestamptz
```

Nao deve existir versao de taxonomia. `source_sha256` serve somente para
auditoria do arquivo carregado.

#### `offers.profile_product_category_quotas`

Politica de categorias e quotas por profile:

```text
profile text
marketplace text
product_cat_id bigint
daily_quantity integer
enabled boolean
source_sha256 text
updated_at timestamptz
```

Regras:

- chave unica `profile + marketplace + product_cat_id`;
- FK de `product_cat_id` para `offers.shopee_product_categories.category_id`;
- `daily_quantity > 0`;
- soma ativa do `feminino/shopee` igual a 140;
- exatamente 46 categorias ativas.

#### `offers.catalog_items`

Adicionar:

```text
product_cat_id bigint
catalog_generation text
catalog_status text
refresh_required_after timestamptz
```

Regras:

- FK de `product_cat_id` para a tabela oficial;
- `catalog_status in ('current', 'legacy')`;
- indice em `profile, marketplace, catalog_status`;
- indice em `profile, marketplace, product_cat_id, catalog_status`;
- manter a unicidade atual por `profile + marketplace + item_id`.

#### Outras superficies

- adicionar `product_cat_id` singular em `offers.offer_snapshots` para auditoria
  da categoria usada no request;
- adicionar `product_cat_id` em `offers.daily_dispatch_plan`;
- expor `product_cat_id` em `v_offer_refresh_status`;
- expor `product_cat_id` em `v_offer_scoring_current`;
- expor `product_cat_id` e ranking por categoria em
  `v_offer_ranking_current`;
- expor `product_cat_id` em `v_daily_dispatch_ready`;
- propagar `product_cat_id` para `v_daily_dispatch_ready_tracked` sem alterar a
  substituicao do link pelo `tracking_short_url`.

Seguranca:

- habilitar RLS nas novas tabelas;
- manter views com `security_invoker = true`;
- revogar acessos indevidos de `anon`, `authenticated` e `PUBLIC`;
- nao criar policy publica;
- nao usar `SECURITY DEFINER` para contornar permissao.

### Supabase - importacao

Entradas:

- catalogo limpo;
- `observed_at` estavel do artefato;
- `catalog_generation` da execucao;
- confirmacao explicita de escrita remota;
- conexao segura via ambiente.

Saidas:

- itens novos inseridos como `current`;
- itens existentes atualizados de forma controlada e promovidos para `current`;
- snapshots com `product_cat_id`;
- historico anterior preservado;
- contagens de novos, atualizados, inalterados e snapshots.

Regras:

- manter idempotencia por
  `profile + marketplace + source_sha256 + observed_at`;
- atualizar somente campos autorizados;
- preservar estado anterior antes do update;
- nao sobrescrever historico comercial sem snapshot;
- nunca fazer hard delete;
- `new_items + updated_existing_items + unchanged_existing_items` deve ser
  igual ao total de linhas limpas e deduplicadas.

### Elegibilidade e ranking

- `rating >= 4.5` em `v_offer_scoring_current` e
  `v_offer_ranking_current`;
- rating nulo deve produzir `is_eligible = false`;
- motivo `rating_below_4_5` para rating abaixo do piso ou nulo;
- item `legacy` deve permanecer consultavel, mas inelegivel para o plano novo;
- ranking de categoria particionado por
  `profile + marketplace + product_cat_id`;
- preservar ranking e campos legados enquanto houver consumidor;
- nao alterar componentes ou pesos de score fora do piso de elegibilidade.

### Refresh e stale forcado

- `refresh_required_after` posterior ao snapshot deve produzir `STALE`;
- ausencia de snapshot deve produzir `MISSING`;
- refresh bem-sucedido posterior ao cutoff deve voltar para `FRESH`;
- falha tecnica nao apaga snapshot anterior;
- refresh deve carregar `product_cat_id` a partir do item do catalogo, nao de
  `productCatIds` do response;
- somente o catalogo `current` participa da preparacao do plano novo;
- o importador nao deve executar refresh automaticamente.

### Planejamento diario

Entradas:

- planner de `productCatId` fornecido pelo usuario;
- 46 quotas canonicas;
- `offers.v_offer_ranking_current`;
- `planned_date` em BRT;
- somente candidatos `current`, elegiveis e `FRESH` no proprio dia.

Saidas:

- 140 linhas em `offers.daily_dispatch_plan`;
- 14 janelas de 10 slots entre 08h e 21h;
- quota exata por `product_cat_id`;
- ready views expondo a categoria singular.

Validacoes:

- nenhuma categoria fora da allowlist;
- soma por categoria igual a matriz canonica;
- nenhum item duplicado no dia;
- nenhuma linha legacy;
- nenhum snapshot anterior ao `planned_date` em BRT;
- falha atomica quando qualquer quota nao puder ser preenchida;
- `replace_day` continua recusando alterar plano consumido;
- o n8n nao recalcula ranking, quota ou categoria.

### VPS e n8n

- atualizar a VPS somente depois de validacao local e Supabase coerente;
- provar igualdade entre commit local, remoto e VPS;
- provar worktree limpa na VPS ou explicar qualquer arquivo operacional local;
- validar migrations pendentes igual a zero;
- reiniciar somente os servicos necessarios;
- validar timer e service de refresh;
- validar `activeVersionId` e `workflowVersionId` efetivos do n8n;
- provar que o workflow WhatsApp ativo consulta
  `offers.v_daily_dispatch_ready_tracked`;
- validar que tracking, short URL, allowlist, claim e registro de publicacao
  continuam intactos;
- nao realizar envio real como parte da validacao automatizada.

## O que nao deve ser alterado

Nao alterar comportamento de:

- assinatura GraphQL;
- credenciais ou arquivos de ambiente;
- envio WhatsApp ou Instagram;
- texto de copy e disclosure;
- templates de mensagem;
- allowlist de destinos;
- tracking de short URL e Sub IDs;
- claim concorrente e `FOR UPDATE SKIP LOCKED`;
- cooldown de publicacao;
- idempotencia de `publication_events`;
- historico de publicacao;
- horarios 08h-21h;
- total diario de 140;
- regra de nao substituir plano consumido;
- snapshots antigos;
- itens antigos por hard delete;
- outros profiles;
- branch Git sem autorizacao explicita.

Nao remover ainda:

- `primary_subniche` e `subniches` legados;
- campos de ranking por subnicho;
- coluna legada `product_cat_ids` que ja exista em snapshot;
- docs legadas.

Esses campos ficam apenas por compatibilidade e nao podem classificar os novos
itens nem dirigir o novo planner.

## Contratos por processo

### 1. Carga da arvore oficial

Entrada: `data/shopee_product_categories.csv`.

Saida: `offers.shopee_product_categories`.

Aceite:

- 1.339 IDs unicos;
- nenhum ID nulo;
- contagem local igual a remota;
- caminho reconstruivel;
- hash da fonte registrado;
- RLS e grants auditados.

### 2. Carga da matriz feminina

Entrada: arquivo versionado `productCatId,daily_quantity`.

Saida: `offers.profile_product_category_quotas`.

Aceite:

- 46 linhas e 46 IDs unicos;
- soma 140;
- todos os IDs presentes na arvore oficial;
- profile `feminino` e marketplace `shopee`;
- nenhuma quantidade menor que 1.

### 3. Discovery

Entrada: `productCatId`.

Saidas: `raw_catalog_productcatid.csv` e `discovery_report.json`.

Aceite:

- toda linha possui `productCatId` e `itemId`;
- toda categoria, inclusive vazia, possui status no relatorio;
- `productCatIds` nao influencia o resultado;
- conflito de item entre categorias bloqueia a execucao.

### 4. Limpeza

Entradas: `raw_catalog_productcatid.csv` e `negative_terms`.

Saidas: `clean_catalog_productcatid_rating_4_5_plus.csv` e
`removed_rows.csv`.

Aceite:

- rating nao nulo e maior ou igual a 4.5;
- nenhum termo proibido;
- um `itemId` por profile;
- `productCatId` pertence a allowlist de 46 IDs;
- todas as remocoes possuem motivo.

### 5. Importacao Supabase

Entrada: `clean_catalog_productcatid_rating_4_5_plus.csv`.

Saidas: `offers.catalog_imports`, `offers.catalog_items`,
`offers.offer_snapshots` e `offers.catalog_item_import_history`.

Aceite:

- dry-run sem escrita;
- apply exige confirmacao literal;
- contagens reconciliadas apos dedupe;
- item legacy reencontrado termina current;
- item antigo ausente permanece legacy apos cutover;
- snapshots e historico preservados.

### 6. Ranking e refresh

Entradas: catalogo, snapshot atual, estado de selecao e politica de refresh.

Saidas: `v_offer_refresh_status`, `v_offer_scoring_current`,
`v_offer_ranking_current` e `offer_refresh_attempts`.

Aceite:

- rating 4.49 inelegivel;
- rating 4.50 elegivel se demais travas passarem;
- rating nulo inelegivel;
- legacy inelegivel para plano novo;
- stale forcado respeita cutoff;
- refresh posterior retorna FRESH;
- ranking por categoria sem posicao duplicada.

### 7. Planejamento e consumo

Entradas: planner fornecido, quotas, ranking e `planned_date`.

Saidas: `daily_dispatch_plan`, `v_daily_dispatch_ready` e
`v_daily_dispatch_ready_tracked`.

Aceite:

- 140 slots e 14 horas de 10 slots;
- quotas por categoria exatamente iguais a matriz;
- somente current, elegivel e FRESH D0;
- tracking ready view preserva short URL;
- n8n ativo consome a view rastreada;
- nenhum plano parcial.

### 8. Cutover e deploy

Entradas: autorizacao explicita, commit, geracao e horario posterior a 21h BRT.

Saidas: catalogo anterior legacy, novo current, refresh e plano seguinte.

Aceite:

- inicio depois das 21h BRT;
- plano encerrado do dia inalterado;
- transacao ou rollback documentado;
- nenhum hard delete;
- nenhuma migration pendente;
- VPS no commit esperado;
- workflow ativo na versao esperada;
- nenhum envio real de validacao.

## Testes automatizados obrigatorios

### Locais

- validar matriz com 46 IDs e soma 140;
- validar todos os IDs contra o CSV oficial;
- rejeitar ID duplicado ou quantidade menor que 1;
- provar que somente `productCatId` singular entra no contrato operacional;
- provar que `productCatIds` nao altera classificacao;
- aceitar rating 4.5 e rejeitar 4.49 e nulo;
- preservar termos proibidos;
- rejeitar item associado a duas categorias;
- promover legacy reencontrado para current;
- manter item ausente como legacy;
- preencher quotas exatas e falhar sem plano parcial;
- preservar horarios, tracking, cooldown, claim e idempotencia.

### Migration e Supabase

- existencia, constraints e indices das novas tabelas e colunas;
- RLS habilitado e ausencia de grants publicos indevidos;
- views com `security_invoker = true`;
- fixtures transacionais para rating, legacy/current e stale;
- 46 quotas e soma 140 no Supabase;
- contagem da arvore oficial igual ao CSV local;
- propagacao de `product_cat_id` ate a ready view rastreada;
- rollback de fixtures sem residuos;
- advisors Supabase sem alerta novo causado pela migration.

Validadores esperados:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\validate_catalog_schema.py
.\.venv\Scripts\python.exe scripts\supabase\validate_shopee_product_categories.py
.\.venv\Scripts\python.exe scripts\supabase\validate_productcatid_catalog_contract.py
.\.venv\Scripts\python.exe scripts\supabase\validate_productcatid_dispatch_readiness.py
```

### VPS e n8n

Criar auditoria automatizada que prove:

```text
GIT_REMOTE=OK
VPS_COMMIT=OK
SUPABASE_MIGRATIONS=OK
REFRESH_SERVICE=OK
N8N_ACTIVE_VERSION=OK
N8N_TRACKED_READY_VIEW=OK
NO_SECRET_OUTPUT=OK
```

O teste deve conferir a versao efetivamente ativa, nao apenas o JSON salvo no
repositorio ou o `active=true` do workflow.

### Loop de validacao

O runner deve:

- executar testes locais primeiro;
- parar no primeiro erro;
- registrar comando, status, tempo, resumo e caminho do relatorio;
- permitir que o agente corrija o erro e inicie nova iteracao;
- limitar a cinco iteracoes por rodada;
- executar validadores Supabase somente com ambiente configurado;
- executar auditoria VPS somente depois de commit e deploy autorizados;
- nunca aplicar migration, fazer deploy ou enviar mensagem sem flag e
  autorizacao explicitas.

O loop executa validacoes; a correcao entre iteracoes e feita pelo agente, nao
pelo proprio script.

## Sequencia de implementacao

### Fase 1 - Configuracao e planner

- receber e revisar o planner fornecido;
- versionar a matriz de 46 categorias;
- provar soma 140 e compatibilidade com 14 janelas;
- nao fazer escrita remota.

### Fase 2 - Discovery e contrato local

- implementar `productCatId` singular;
- remover taxonomia interna do novo caminho;
- preservar termos proibidos;
- alterar rating para 4.5;
- rodar testes locais.

### Fase 3 - Schema Supabase

- criar migration aditiva;
- criar tabelas, colunas, indices e views;
- validar RLS, grants e `security_invoker`;
- nao executar cutover.

### Fase 4 - Importacao controlada

- implementar dry-run e staging idempotente por `catalog_generation`;
- validar que todos os candidatos pertencem a uma das 46 categorias ativas;
- manter o lote inerte ate o cutover, sem escrever em `catalog_items` ou
  `offer_snapshots`;
- no cutover, preservar historico de linhas atualizadas e validar promocao
  `legacy` para `current`.

### Fase 5 - Ranking, refresh e planner

- propagar categoria singular;
- alterar elegibilidade para 4.5;
- integrar planner fornecido;
- validar 140 slots e quotas exatas;
- propagar categoria ate `v_daily_dispatch_ready_tracked`;
- nao alterar tracking, copy ou envio.

### Fase 6 - Deploy tecnico

- confirmar branch antes de commit ou push;
- enviar commit autorizado ao remoto;
- aplicar migrations autorizadas;
- atualizar VPS;
- validar commit, services e workflow ativo;
- ainda nao executar cutover.

### Fase 7 - Cutover depois das 21h

1. Confirmar horario BRT posterior a 21h.
2. Auditar e registrar o plano encerrado do dia.
3. Registrar estado current anterior para rollback.
4. Marcar catalogo feminino atual como legacy.
5. Importar ou promover o novo catalogo como current.
6. Aplicar `refresh_required_after` ao current.
7. Reconciliar contagens legacy/current e categorias.
8. Executar refresh do current.
9. Validar cobertura FRESH de todas as 46 quotas.
10. Gerar o plano do dia seguinte com 140 slots.
11. Validar ready view base e rastreada.
12. Validar n8n ativo sem realizar envio real.

## Criterios de aceite final

1. A matriz versionada tem 46 IDs unicos e soma 140.
2. Todos os IDs existem na tabela oficial e no CSV local.
3. O discovery usa somente `productCatId` singular.
4. `productCatIds` nao influencia nenhum processo operacional.
5. Todo item novo pertence ao profile `feminino`.
6. O catalogo local preserva `productCatId`.
7. Rating 4.5 e aceito; 4.49 e nulo sao rejeitados.
8. Termos proibidos continuam ativos.
9. Nenhuma taxonomia interna classifica item novo.
10. Existe um unico catalogo persistente com status current/legacy.
11. Item legacy reencontrado termina current.
12. Item antigo ausente permanece legacy, sem hard delete.
13. Conflito de item entre categorias bloqueia a importacao.
14. Supabase armazena arvore oficial, quotas e categoria do item.
15. Ranking, refresh e fila expoem `product_cat_id`.
16. Planner gera 140 slots e cumpre cada quota.
17. Plano parcial nunca e persistido.
18. `v_daily_dispatch_ready_tracked` preserva tracking e categoria.
19. O workflow n8n efetivamente ativo consome a view rastreada.
20. Cutover acontece depois das 21h BRT.
21. Plano encerrado do dia permanece inalterado.
22. Current fica stale ou missing ate refresh real posterior ao cutoff.
23. Plano seguinte so e gerado com cobertura FRESH suficiente.
24. Supabase fica sem migration pendente.
25. VPS fica no commit remoto esperado.
26. Testes locais, SQL, Supabase, VPS e n8n passam.
27. Nenhum segredo e impresso.
28. Nenhum envio real ocorre durante validacao.

## Evidencias obrigatorias ao finalizar

- branch ativa;
- commit local, remoto e VPS;
- migrations aplicadas e pendentes igual a zero;
- resultado de Ruff e pytest;
- resultado dos testes SQL e validadores Supabase;
- 1.339 categorias oficiais carregadas;
- 46 quotas ativas e soma 140;
- contagem de itens legacy e current;
- contagem current por `product_cat_id` e `refresh_status`;
- prova de 140 slots e quotas exatas no plano seguinte;
- amostra das ready views com `product_cat_id`;
- `activeVersionId`, `workflowVersionId` e query efetiva do n8n;
- prova de preservacao de tracking e short URL;
- confirmacao de que o plano encerrado nao mudou;
- confirmacao de que nenhum segredo foi impresso;
- confirmacao de que nenhum envio real foi executado.

## Autorizacoes ainda necessarias

Estas nao sao decisoes de produto pendentes. Sao boundaries operacionais que
devem ser confirmadas no momento correspondente:

- receber o arquivo ou codigo do planner de `productCatId`;
- autorizar commit e push na branch ativa;
- autorizar migrations adicionais que sejam necessarias especificamente para o
  cutover;
- autorizar atualizacao e restart necessario na VPS;
- autorizar o cutover depois das 21h BRT;
- qualquer envio real continua fora do escopo desta implementacao.

## Prompt para implementar esta spec

```text
Implemente a spec docs/projeto/12-spec-catalogo-productcatid-shopee.md.

Antes de editar, leia AGENTS.md, docs/supabase-catalog-schema.md,
docs/candidate-refresh-pipeline.md e esta spec. Receba e revise o planner de
productCatId fornecido pelo usuario.

Trabalhe na branch ativa verificada. Nao crie ou troque branch. Implemente as
fases na ordem documentada, rode os testes relevantes, corrija falhas e repita
ate passar ou encontrar bloqueio real.

Nao use productCatIds do response. O unico eixo operacional e productCatId
singular definido na matriz feminina. Preserve tracking, copy, horarios,
cooldown, allowlist, claim, idempotencia e demais comportamentos existentes.

Migration, deploy e cutover exigem autorizacoes separadas. Execute o cutover
somente depois das 21h BRT e somente como ultima etapa. Nao realize envio real.

No final, prove config -> caller -> persistence -> downstream consumer, a soma
de 140 quotas, o plano seguinte com 140 slots, Supabase sem migration pendente,
VPS no commit esperado e n8n ativo consumindo a ready view rastreada.
```

## Commit sugerido

```text
docs(catalogo): consolida decisoes por productcatid
```

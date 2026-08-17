# Analise do catalogo Shopee ativo versus Product Feeds

> Nota de modelo: esta analise registra o catalogo ativo existente na data da
> coleta. Depois da migration incremental, novas execucoes da ferramenta usam o
> catalogo persistente e nao filtram `catalog_imports.status = 'active'`.

Data da analise: 2026-08-11

## Escopo

Esta analise foi executada em modo estritamente read-only.

Foram usados apenas:

- leitura de codigo e documentacao do repositorio;
- leitura dos CSVs locais dos feeds;
- `SELECT` contra o Supabase;
- geracao de artefatos locais de analise em `.data/feed_vs_catalog_analysis/2026-08-11/`.

Nada foi inserido, atualizado, removido ou reimportado no banco.

## Fontes usadas

Catalogo ativo no Supabase:

- `offers.catalog_imports`
- `offers.catalog_items`
- `offers.v_offer_ranking_current`

Arquivos locais usados para enriquecer o snapshot ativo sem alterar o banco:

- `catalogs/processed/auto-e-moto/shopee_catalogo_limpo_subniches.csv`
- `catalogs/processed/feminino/shopee_catalogo_limpo_subniches.csv`
- `catalogs/processed/mae-e-bebe/shopee_catalogo_limpo_subniches.csv`

Feeds locais lidos em `C:\Users\arthu\Downloads`:

- `1005_200149_Shopee Brasil - 2022_20260811T045216_1.csv` (10k)
- `1005_200150_Shopee Oficial BR - 2022_20260811T045216_1.csv` (100k)

Codigo e contratos consultados:

- `docs/supabase-catalog-schema.md`
- `docs/status-integracao-shopee.md`
- `src/ofertas_bot/catalog_contract.py`
- `src/ofertas_bot/providers/shopee.py`
- `src/ofertas_bot/providers/shopee_graphql.py`

## Reproducao

Comando usado:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts\shopee\analyze_product_feeds.py --run-id 2026-08-11
```

Artefatos locais gerados:

- `.data/feed_vs_catalog_analysis/2026-08-11/summary.json`
- `.data/feed_vs_catalog_analysis/2026-08-11/catalog_vs_feed100k_overlap.csv`
- `.data/feed_vs_catalog_analysis/2026-08-11/catalog_vs_feed10k_overlap.csv`
- `.data/feed_vs_catalog_analysis/2026-08-11/feed10k_vs_feed100k_overlap.csv`

Consulta SQL usada para carregar o catalogo ativo:

```sql
select
  imp.id as import_id,
  imp.profile,
  imp.marketplace,
  imp.row_count,
  item.item_id,
  item.product_name,
  item.product_link,
  item.offer_link,
  item.image_url,
  item.price,
  item.reference_price,
  item.sales_count,
  item.rating,
  item.shop_type_codes,
  item.seller_commission_rate,
  item.shopee_commission_rate,
  item.commission_rate_fallback,
  item.is_free_shipping,
  item.subniches,
  item.source_payload
from offers.catalog_imports imp
join offers.catalog_items item
  on item.import_id = imp.id
where imp.status = 'active'
order by imp.profile, item.item_id;
```

## Diagnostico das fontes

Snapshot ativo atual no Supabase:

- `auto-e-moto`: 11.560 linhas
- `feminino`: 27.292 linhas
- `mae-e-bebe`: 7.164 linhas
- total: 46.016 linhas

Importante:

- o catalogo ativo no Supabase nao guarda `shopId` como coluna;
- o `shopId` foi reconstituido a partir de `product_link` no formato `/product/<shopId>/<itemId>`;
- a cobertura dessa reconstrucao foi total: 46.016 de 46.016 linhas, com 100% de consistencia contra os CSVs `catalogs/processed/*`;
- categoria Shopee nao sobreviveu como coluna no catalogo ativo;
- para comparar categoria, foi necessario enriquecer o snapshot ativo com `productCatIds` dos CSVs `catalogs/processed/*`;
- `subniches` no Supabase continuam sendo a taxonomia curada interna, nao a categoria nativa da Shopee.

## Mapeamento de schema

| Conceito | Catalogo ativo | Feed 100k | Feed 10k |
| --- | --- | --- | --- |
| `itemId` | `offers.catalog_items.item_id` | `itemid` | `itemid` |
| `shopId` | derivado de `product_link` e validado contra `catalogs/processed/*::shopId` | derivado de `product_link` | derivado de `product_link` |
| `shopName` | `catalogs/processed/*::shopName` | `shop_name` | nao disponivel |
| categoria nivel 1 id | `productCatIds[0]` via `catalogs/processed/*` | `global_catid1` | `global_catid1` |
| categoria nivel 2 id | `productCatIds[1]` via `catalogs/processed/*` | `global_catid2` | `global_catid2` |
| categoria nivel 3 id | `productCatIds[2]` via `catalogs/processed/*` | `global_catid3` | nao disponivel |
| nome do produto | `product_name` | `title` | `title` |
| preco atual | `price` | `sale_price` | `sale_price` |
| preco de referencia | `reference_price` | `price` | `price` |
| desconto | derivado de `reference_price` vs `price` | `discount_percentage` | `discount_percentage` |
| vendas | `sales_count` | nao disponivel | nao disponivel |
| rating do item | `rating` | `item_rating` | `item_rating` |
| rating da loja | nao disponivel | `shop_rating` | nao disponivel |
| tipo de loja | `shop_type_codes` | nao disponivel | nao disponivel |
| taxonomia interna | `subniches` | nao disponivel | nao disponivel |

## Auditoria basica

| Conjunto | Linhas | `itemId` distintos | `shopId` distintos | `itemId` nulos | `shopId` nulos | Duplicados por `itemId` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Catalogo ativo | 46.016 | 45.709 | 13.583 | 0 | 0 | 307 |
| Feed 100k | 100.000 | 100.000 | 2.187 | 0 | 0 | 0 |
| Feed 10k | 10.000 | 10.000 | 7.326 | 0 | 0 | 0 |

Observacoes:

- no catalogo ativo existem 307 `itemId` duplicados;
- esses duplicados sao cross-profile, nao duplicidade interna do mesmo profile;
- exemplos observados: itens presentes ao mesmo tempo em `feminino` e `mae-e-bebe`, ou em `auto-e-moto` e `feminino`;
- nos feeds, os joins precisaram normalizar `itemid` e `shopId` como texto canonico de digitos;
- no Supabase o `item_id` e `bigint`, enquanto nos CSVs os campos entram como texto.

## Overlap por itemId

### Catalogo ativo x Feed 100k

Por `itemId`:

- catalogo: 45.709 itens distintos
- feed 100k: 100.000 itens distintos
- interseccao: 528
- somente catalogo: 45.181
- somente feed 100k: 99.472
- 1,1551% do catalogo aparece no feed 100k
- 0,5280% do feed 100k aparece no catalogo

Por `itemId + shopId`:

- mesmo resultado: 528

Leitura:

- quando um `itemId` bate, o `shopId` tambem bate;
- o gargalo nao e colisao de chave, e sim ausencia do item no outro universo.

### Catalogo ativo x Feed 10k

Por `itemId`:

- catalogo: 45.709
- feed 10k: 10.000
- interseccao: 96
- 0,2100% do catalogo aparece no feed 10k
- 0,9600% do feed 10k aparece no catalogo

### Feed 10k x Feed 100k

Por `itemId`:

- feed 10k: 10.000
- feed 100k: 100.000
- interseccao: 364
- 3,64% do feed 10k aparece no feed 100k

Conclusao objetiva:

- o feed 10k nao e subconjunto do feed 100k.

## Validacao do numero "aproximadamente 206"

O overlap de `aproximadamente 206` nao se confirmou quando o universo comparado foi o catalogo ativo completo do Supabase.

Resultado reproduzivel desta analise:

- overlap correto do catalogo ativo completo x feed 100k: 528 `itemId`s distintos.

O que explica a divergencia:

- o catalogo ativo completo hoje tem 46.016 linhas e 45.709 `itemId`s distintos;
- os testes exploratorios anteriores usavam recortes menores;
- foi possivel reproduzir outros numeros menores ao mudar o universo, por exemplo:
  - 149 para os primeiros 10k itens do CSV local `catalogs/clean/feminino/clean_catalog_rating_4_8_plus.csv`;
  - 399 para o recorte dos itens com `rank_profile <= 10000` em `offers.v_offer_ranking_current`;
- portanto, o `206` nao representa o overlap atual do catalogo ativo inteiro; ele provavelmente veio de um recorte anterior diferente, que nao estava documentado como base oficial.

Os dados disponiveis hoje nao permitem reconstruir com seguranca exatamente qual era o recorte que gerou `206`.

## Overlap por shopId

### Catalogo ativo x Feed 100k

- lojas distintas no catalogo: 13.583
- lojas distintas no feed 100k: 2.187
- lojas em comum: 355
- somente catalogo: 13.228
- somente feed: 1.832
- 2,6136% das lojas do catalogo aparecem no feed 100k
- 16,2323% das lojas do feed 100k aparecem no catalogo

Itens em lojas compartilhadas:

- 3.399 itens do catalogo pertencem a lojas que tambem aparecem no feed 100k
- 31.313 itens do feed 100k pertencem a lojas que tambem aparecem no catalogo

Leitura:

- ha muito mais itens em lojas compartilhadas do que itens exatamente iguais;
- 3.399 versus 528 mostra que, dentro das lojas em comum, o feed 100k frequentemente escolhe SKUs diferentes dos SKUs do catalogo;
- ao mesmo tempo, 355 de 13.583 lojas em comum e um overlap baixo no lado do catalogo mostram que tambem existe uma diferenca forte de universo de sellers.

Diagnostico do cenario:

- o comportamento observado e uma combinacao dos cenarios A e B;
- existe efeito claro de selecao de SKUs diferentes dentro de lojas compartilhadas;
- existe tambem um recorte relevante de lojas diferentes, principalmente quando se olha do catalogo para o feed 100k.

### Catalogo ativo x Feed 10k

- lojas em comum: 898
- 6,6112% das lojas do catalogo aparecem no feed 10k
- 12,2577% das lojas do feed 10k aparecem no catalogo

### Feed 10k x Feed 100k

- lojas distintas no feed 10k: 7.326
- lojas distintas no feed 100k: 2.187
- lojas em comum: 172
- 2,3478% das lojas do feed 10k aparecem no feed 100k
- 7,8647% das lojas do feed 100k aparecem no feed 10k

## Concentracao por loja

### Catalogo ativo

- mediana de produtos por loja: 1
- media: 3,39
- p75: 3
- p90: 7
- p95: 11

Top loja por quantidade:

- `Choice Oficial`: 1.317 itens

### Feed 100k

- mediana de produtos por loja: 15
- media: 45,72
- p75: 43
- p90: 104
- p95: 169,7

Top lojas por quantidade:

- `Gomec Auto Peças SP`: 1.732
- `MadeiraMadeira`: 1.512
- `Rizzo Distribuidora`: 1.360

### Feed 10k

- mediana de produtos por loja: 1
- media: 1,37
- p75: 1
- p90: 2
- p95: 3

Leitura:

- o feed 100k e altamente concentrado em poucas lojas com muitos SKUs;
- o feed 10k e extremamente difuso, com cauda longa de sellers e pouco volume por seller;
- o catalogo ativo fica muito mais perto do feed 10k em densidade por seller do que do feed 100k.

## Comparacao por categoria

Como o Supabase nao guarda o nome da categoria Shopee no snapshot ativo, a comparacao foi feita pelos IDs hierarquicos `productCatIds` versus `global_catid1/2/3`.

### Nivel 1 mais representado no feed 100k

| Categoria | Catalogo | Feed 100k | Share catalogo | Share feed 100k |
| --- | ---: | ---: | ---: | ---: |
| `102187` Spare Parts and Accessories for Vehicles | 6.087 | 29.758 | 13,2280% | 29,7580% |
| `100636` Home & Living | 2.295 | 22.072 | 4,9874% | 22,0720% |
| `100630` Beauty | 7.947 | 8.173 | 17,2701% | 8,1730% |
| `100632` Mom & Baby | 6.404 | 3.194 | 13,9169% | 3,1940% |

Leitura:

- o feed 100k super-representa `Spare Parts and Accessories for Vehicles` e `Home & Living`;
- o catalogo ativo super-representa `Beauty` e `Mom & Baby` em relacao ao feed 100k.

### Nivel 2 com diferencas mais fortes

| Categoria | Catalogo | Feed 100k | Share catalogo | Share feed 100k |
| --- | ---: | ---: | ---: | ---: |
| `102224` Spare Parts for Automobiles | 657 | 17.804 | 1,4278% | 17,8040% |
| `100713` Furniture | 228 | 7.397 | 0,4955% | 7,3970% |
| `100659` Hair Care | 1.236 | 2.840 | 2,6860% | 2,8400% |
| `102249` Internal Accessories for Automobiles | 1.668 | 2.099 | 3,6248% | 2,0990% |

Leitura:

- autopecas domina o feed 100k em profundidade;
- `Furniture` e outro bloco muito forte no 100k;
- `Hair Care` aparece nos dois universos, mas nao o suficiente para explicar o baixo overlap geral.

## Comparacao de atributos

## Catalogo ativo completo

- preco mediano: 45,49
- desconto mediano: 25,0190%
- rating mediano: 4,9
- vendas medianas: 9

## Feed 100k completo

- preco mediano: 89,495
- desconto mediano: 0%
- rating mediano do item: 5,0
- rating mediano da loja: 4,89
- vendas: nao disponivel

## Feed 10k completo

- preco mediano: 34,90
- desconto mediano: 12%
- rating mediano do item: 4,88
- vendas: nao disponivel

Leitura:

- o feed 100k tem preco muito mais alto que o catalogo ativo;
- o feed 10k tem preco mediano mais baixo que ambos;
- o catalogo ativo e muito mais orientado a desconto do que o feed 100k;
- o feed 100k tem nota muito alta, mas isso nao diferencia tanto do catalogo porque ambos estao em faixas altas.

## Itens em comum

Grupo `catalogo ∩ feed 100k`:

- 528 `itemId`s distintos
- 533 linhas no lado do catalogo, por causa de alguns `itemId`s presentes em mais de um profile
- 157 lojas distintas
- preco mediano: 68,00
- rating mediano: 4,9
- vendas medianas no catalogo: 10

Comparacao:

- a interseccao tem preco mediano acima do catalogo completo (`68,00` vs `45,49`);
- a interseccao continua muito abaixo do preco mediano do feed 100k (`68,00` vs `89,495`);
- a mediana de vendas da interseccao (`10`) fica praticamente em linha com o catalogo completo (`9`);
- nao ha evidencia de que a interseccao seja definida por vendas muito maiores.

## Analise do feed 10k

O feed 10k estava disponivel localmente e foi analisado.

Principais achados:

- nao e subconjunto do feed 100k por `itemId`;
- nao e subconjunto do feed 100k por `itemId + shopId`;
- nao e subconjunto do feed 100k por `shopId`;
- tem muito mais sellers distintos proporcionalmente do que o feed 100k;
- tem preco mediano menor;
- tem desconto mediano maior;
- nao possui `shop_name`;
- nao possui `shop_rating`;
- nao possui vendas.

Leitura:

- o feed 10k parece seguir um criterio de amostragem muito diferente do feed 100k;
- ele nao se comporta como "um corte simples dos mesmos sellers e mesmos itens".

## Tabela-resumo

| Metrica | Catalogo | Feed 100k | Feed 10k | Interseccao Cat/100k | Somente catalogo | Somente 100k |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Linhas | 46.016 | 100.000 | 10.000 | 533 | 45.483 | 99.472 |
| Produtos distintos | 45.709 | 100.000 | 10.000 | 528 | 45.181 | 99.472 |
| Lojas distintas | 13.583 | 2.187 | 7.326 | 157 | 13.568 | 2.186 |
| Preco mediano | 45,49 | 89,495 | 34,90 | 68,00 | 45,00 | 89,90 |
| Desconto mediano | 25,0190% | 0% | 12% | 19,7791% | 25,0271% | 0% |
| Rating mediano | 4,9 | 5,0 | 4,88 | 4,9 | 4,9 | 5,0 |
| Vendas medianas | 9 | n/d | n/d | 10 | 9 | n/d |
| Produtos/loja mediano | 1 | 15 | 1 | 1 | 1 | 15 |

## Fatos observados

- O catalogo ativo completo tem 45.709 `itemId`s distintos, nao 42 mil.
- O overlap correto do catalogo ativo completo com o feed 100k e 528 `itemId`s distintos.
- Esse overlap representa 1,1551% do catalogo e 0,5280% do feed 100k.
- O overlap por `itemId` e por `itemId + shopId` e o mesmo.
- Catalogo e feed 100k compartilham 355 lojas.
- 3.399 itens do catalogo pertencem a lojas que tambem aparecem no feed 100k.
- 31.313 itens do feed 100k pertencem a lojas que tambem aparecem no catalogo.
- O feed 100k tem apenas 2.187 lojas para 100.000 itens.
- O feed 10k tem 7.326 lojas para 10.000 itens.
- O feed 10k compartilha apenas 364 `itemId`s com o feed 100k.
- O feed 10k nao esta contido no feed 100k.
- O feed 100k super-representa autopecas e `Home & Living`.
- O catalogo ativo super-representa `Beauty` e `Mom & Baby`.
- Os feeds nao trazem vendas.
- O feed 10k nao traz `shop_name`.
- O feed 100k traz `shop_rating`; o feed 10k nao.

## Inferencias suportadas

- O baixo overlap nao e causado por problema de join, porque `itemId` e `itemId + shopId` produzem o mesmo resultado.
- Parte importante da diferenca vem de universo de sellers diferente.
- Outra parte importante vem de selecao de SKUs diferentes dentro das lojas compartilhadas.
- O feed 100k parece priorizar poucos sellers com portfolios grandes.
- O feed 10k parece distribuir itens por muito mais sellers, com baixa densidade por seller.
- O catalogo ativo se parece mais com o feed 10k na distribuicao por seller do que com o feed 100k.
- O mismatch de categorias ajuda a explicar o baixo overlap: o 100k e puxado por autopecas e casa; o catalogo ativo tem peso muito maior em beleza e mae e bebe.

## Hipoteses nao comprovadas

- A Shopee pode estar aplicando criterio comercial interno especifico para decidir quem entra no feed 100k.
- Comissao pode influenciar a presenca no feed, mas esta analise nao pode comprovar isso porque os feeds locais nao carregam comissao.
- Pode existir regra de elegibilidade por seller, loja oficial, campanha, disponibilidade, estoque ou performance historica que nao aparece nesses CSVs.
- Pode existir logica de rotacao ou janelas temporais diferentes entre o feed 10k e o feed 100k.

Os dados disponiveis nao permitem concluir o algoritmo interno exato de selecao da Shopee.

## Etapa futura sugerida para comissao

Nao foi feita nenhuma chamada de API nesta etapa.

Com base no codigo atual:

- endpoint relevante: `productOfferV2`
- evidencias no repo:
  - `src/ofertas_bot/providers/shopee.py`
  - `src/ofertas_bot/providers/shopee_graphql.py`
  - `docs/status-integracao-shopee.md`
- o codigo atual aceita `itemId` singular por chamada;
- nao foi encontrado suporte observado a batch de lista de `itemId`s;
- `productOfferV2` esta documentada com `limit` padrao de 20 por pagina, mas isso nao equivale a batch por varios `itemId`s;
- `getItemFeedData` esta documentado com ate 500 registros por pagina, mas isso e para download do feed, nao para enriquecer comissao por `itemId`.

Amostragem recomendada para uma fase 2:

- ate 200 itens da interseccao catalogo x feed 100k
- 500 a 1.000 itens somente catalogo
- 500 a 1.000 itens somente feed 100k
- 250 a 500 itens do feed 10k

Estimativa de chamadas se continuar sendo 1 `itemId` por chamada:

- minimo util: cerca de 1.450 chamadas
- faixa alta recomendada: cerca de 2.700 chamadas

## Limitacoes

- O catalogo ativo do Supabase nao preserva `shopId` nem categoria Shopee como colunas diretas.
- A comparacao de categorias depende dos CSVs `catalogs/processed/*`.
- O feed 10k nao preserva `shop_name`.
- Os feeds nao preservam vendas.
- O numero `206` nao foi reproduzivel como overlap do catalogo ativo completo; apenas foi possivel demonstrar que ele pertence a algum recorte menor anterior.

## Resposta objetiva para a pergunta principal

Por que um catalogo com aproximadamente 42 mil produtos possui apenas aproximadamente 206 itens em comum com um Product Feed de aproximadamente 100 mil?

Resposta factual atualizada:

- o catalogo ativo completo hoje nao tem aproximadamente 42 mil, e sim 45.709 `itemId`s distintos;
- o overlap correto atual com o feed 100k nao e aproximadamente 206, e sim 528;
- mesmo assim, o overlap continua muito pequeno porque os dados mostram uma combinacao de:
  - recorte forte de sellers;
  - recorte forte de categorias;
  - e selecao de SKUs diferentes dentro das lojas compartilhadas.

Nao foi encontrada evidencia de erro de chave ou erro de importacao que, sozinho, explique o baixo overlap.

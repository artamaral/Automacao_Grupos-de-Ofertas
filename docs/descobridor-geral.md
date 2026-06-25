# Descobridor Geral

O `descobridor-geral` e o metodo operacional inicial para descoberta de itens
na Shopee a partir de um nicho configurado.

Ele nasce da validacao pratica feita contra a API real da Shopee e deve ser
lido como um metodo de descoberta em duas etapas:

1. chamar `shopeeOfferV2(keyword: ...)`;
2. usar `categoryId` retornado por `shopeeOfferV2` em
   `productOfferV2(listType: 4, matchId: categoryId, ...)`.

## Escopo atual

Neste momento, o `descobridor-geral` vale apenas para Shopee.

Motivo:

- a sequencia foi descoberta e validada na API GraphQL de afiliados da Shopee;
- os contratos usados dependem de queries e ids internos da Shopee;
- outros marketplaces podem exigir sequencias diferentes, outros ids e outras
  regras de descoberta.

Regra operacional:

- perfis podem declarar `discovery_method = "descobridor-geral"` mesmo quando o
  profile ainda estiver em `marketplace = "mock"`;
- isso registra a intencao operacional do nicho;
- a execucao real do metodo depende de um fluxo Shopee compativel.

## O que o metodo quer resolver

O objetivo do metodo e simplificar a vida do operador.

Em vez de o usuario lembrar manualmente quais queries chamar e em que ordem, o
profile do nicho passa a declarar:

- qual termo exato deve entrar em `keyword` na `shopeeOfferV2`;
- opcionalmente, quais ids internos ja foram descobertos e validados;
- qual metodo de descoberta aquele nicho deve usar.

## Sequencia validada ate aqui

### Etapa 1 - `shopeeOfferV2`

Usar `shopeeOfferV2` com o termo exato configurado para o parametro
`keyword`.

Exemplo validado:

- nicho: `mae e bebe`
- keyword: `Mom & Baby`

Campos relevantes observados nessa etapa:

- `offerName`
- `offerType`
- `originalLink`
- `categoryId`
- `commissionRate`

Leitura operacional:

- `shopeeOfferV2` nao e uma boa busca aberta por nicho;
- ela funciona melhor quando recebe um valor exato no parametro `keyword`;
- o resultado serve como ponte para a etapa seguinte via `categoryId`.

### Etapa 2 - `productOfferV2`

Usar `productOfferV2` com:

- `listType = 4` (`DETAIL_CATEGORY`)
- `matchId = categoryId` retornado pela etapa anterior

Exemplo validado:

- `categoryId = 100632`

Leitura operacional:

- a query retorna itens reais e paginados;
- o conjunto retornado e dinamico;
- a resposta nao deve ser tratada como catalogo fixo nem como comparacao
  deterministica entre duas execucoes.
- a coleta deve continuar pagina por pagina ate `hasNextPage = false`;
- se a API responder algo equivalente a `page not found`, isso deve ser tratado
  como parada segura daquela lista.

### Regra de cobertura

Para o `descobridor-geral`, a regra operacional passa a ser:

- na etapa `shopeeOfferV2`, usar no maximo `50` registros por chamada;
- sempre tentar varrer a lista inteira;
- usar `50` itens por pagina;
- aceitar ate `50` paginas por match id como teto operacional;
- portanto, o teto planejado e de `2500` itens por match id;
- ainda assim, a parada real deve acontecer por `hasNextPage = false` ou por
  `page not found`.

Isso existe para garantir que a descoberta nao fique restrita a primeira pagina
quando o nicho tiver lista longa.

### Teto observado ate aqui

Nas validacoes reais feitas com o caminho de categoria do `descobridor-geral`
(`productOfferV2` com `listType = 4` e `matchId = categoryId`), os nichos
`mae-e-bebe` e `pets` encerraram em:

- `10` paginas;
- `50` itens por pagina;
- `500` itens observados no total;
- parada por `hasNextPage = false`.

Isso deve ser tratado como teto observado desse uso de
`productOfferV2(listType: 4, matchId: categoryId)`, e nao
como limite global da `productOfferV2`.

Em validacao real separada, usando:

- `listType = 1`
- `sortType = 2`
- `isKeySeller = true`

a mesma `productOfferV2` retornou:

- `40` paginas;
- `1959` itens observados no total;
- ultima pagina com `9` itens;
- parada por `hasNextPage = false`.

Portanto, a leitura correta passa a ser:

- `500` e um teto observado no uso de `productOfferV2(listType: 4, matchId: categoryId)` ja testado;
- nao existe evidencia atual de teto global em `500` para a query inteira;
- o teto teorico operacional continua sendo `2500` quando a rota permitir.

Tambem fica definido que o `limit` operacional final do fluxo nao deve ser
reaproveitado como `limit` da etapa `shopeeOfferV2`, porque essa etapa aceita
no maximo `50`.

## Interpretacao do resultado

O `descobridor-geral` e um metodo de descoberta, nao um contrato de igualdade
exata entre chamadas.

Isso significa:

- duas execucoes podem retornar itens diferentes;
- o resultado de `productOfferV2(listType: 4, matchId: categoryId)` pode
  misturar itens muito aderentes com alguns ruidosos;
- o resultado precisa de filtro posterior por relevancia do nicho.

Portanto, a avaliacao correta do metodo deve olhar:

- aderencia media ao nicho;
- volume util de itens;
- cobertura comercial;
- estabilidade suficiente para automacao;
- qualidade dos ids e links retornados.

## Configuracao no profile

O lugar correto para declarar o metodo e:

```text
config/discovery_profiles.toml
```

Campos usados por este metodo:

| Campo | Uso |
| --- | --- |
| `discovery_method` | Nome interno do metodo operacional do projeto. Nao e nome de campo da API. |
| `shopee_offer_keyword` | Campo principal. Valor exato enviado como `keyword` para `shopeeOfferV2`. |
| `shopee_product_match_ids` | Opcional. Fallback manual caso `matchId` ja seja conhecido. |

Exemplo resumido:

```toml
[[profiles]]
slug = "mae-e-bebe"
name = "Mae e Bebe"
niche = "mae e bebe"
marketplace = "mock"
discovery_method = "descobridor-geral"
shopee_offer_keyword = "Mom & Baby"
```

Regra pratica:

- para um teste novo, tente primeiro apenas `shopee_offer_keyword`;
- so adicione `shopee_product_match_ids` se precisar de override ou fallback;
- `shopee_category_urls` e `shopee_product_category_ids` nao fazem parte do
  caminho minimo do metodo.

## Regra de nomenclatura

Nesta documentacao:

- nomes de query devem aparecer exatamente como na API: `shopeeOfferV2`,
  `shopOfferV2`, `productOfferV2`, `listItemFeeds`, `getItemFeedData`;
- nomes de parametro devem aparecer exatamente como na API: `keyword`,
  `listType`, `matchId`, `sortType`, `page`, `limit`, `itemId`, `shopId`,
  `productCatId`, `isAMSOffer`, `isKeySeller`;
- nomes internos do projeto devem ser tratados explicitamente como nomes
  internos, por exemplo `descobridor-geral`.

## Por que esse nome

O nome `descobridor-geral` foi escolhido porque este e o primeiro metodo
operacional de descoberta do projeto, pensado para servir como base.

No futuro, outros metodos podem coexistir, por exemplo:

- um metodo especifico para feed em lote da Shopee;
- um metodo de descoberta por seller;
- um metodo diferente para Amazon;
- um metodo curado/manual para marketplaces com contrato mais fraco.

Por isso, o metodo precisa ser declarado no profile em vez de ficar escondido no
codigo.

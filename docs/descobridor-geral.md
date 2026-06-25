# Descobridor Geral

O `descobridor-geral` e o metodo operacional inicial para descoberta de itens
na Shopee a partir de um nicho configurado.

Ele nasce da validacao pratica feita contra a API real da Shopee e deve ser
lido como um metodo de descoberta em duas etapas:

1. encontrar a campanha, vitrine ou categoria afiliada do nicho;
2. usar o identificador retornado para buscar os itens associados.

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

- quais offer names conhecidos representam o nicho na Shopee;
- quais URLs publicas de categoria ajudam a orientar a curadoria;
- quais ids internos ja foram descobertos e validados;
- qual metodo de descoberta aquele nicho deve usar.

## Sequencia validada ate aqui

### Etapa 1 - descoberta da campanha/categoria

Usar `shopeeOfferV2` com um `offer name` conhecido do nicho.

Exemplo validado:

- nicho: `mae e bebe`
- offer name: `Mom & Baby`

Essa etapa tende a devolver:

- `offerName`
- `offerType`
- `originalLink`
- `categoryId`
- `commissionRate`

Leitura operacional:

- `shopeeOfferV2` nao e uma boa busca aberta por nicho;
- ela funciona melhor quando recebe o nome da oferta/campanha conhecido;
- o resultado serve como ponte para a etapa seguinte.

### Etapa 2 - descoberta dos itens

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

## Interpretacao do resultado

O `descobridor-geral` e um metodo de descoberta, nao um contrato de igualdade
exata entre chamadas.

Isso significa:

- duas execucoes podem retornar itens diferentes;
- a categoria comercial da Shopee pode misturar itens muito aderentes com
  alguns ruidosos;
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
| `discovery_method` | Nome do metodo operacional do nicho. |
| `shopee_offer_names` | Offer names conhecidos para a etapa `shopeeOfferV2`. |
| `shopee_category_urls` | URLs publicas de apoio para curadoria e mapeamento. |
| `shopee_product_match_ids` | Match ids internos ja validados para `productOfferV2`. |
| `shopee_product_category_ids` | Category ids publicos/operacionais conhecidos. |

Exemplo resumido:

```toml
[[profiles]]
slug = "mae-e-bebe"
name = "Mae e Bebe"
niche = "mae e bebe"
marketplace = "mock"
discovery_method = "descobridor-geral"
shopee_offer_names = ["Mom & Baby"]
shopee_category_urls = ["https://shopee.com.br/Baby-Kids-Fashion-cat.11059973"]
shopee_product_match_ids = [100632]
shopee_product_category_ids = [11059973]
```

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

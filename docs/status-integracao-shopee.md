# Status da integraÃ§Ã£o Shopee

Este arquivo registra o ponto exato em que a integraÃ§Ã£o real com a Shopee foi pausada, para retomada futura sem perda de contexto.

## Status atual

**Status:** contrato real identificado como GraphQL e base de provider implementada no codigo.
A integracao ainda aguarda chamada real controlada com credenciais aprovadas
para validar resposta de producao.

A conta Shopee e a Open API de afiliados devem ser tratadas pelo contrato
GraphQL informado para o projeto. O contrato REST usado antes no cÃ³digo fica
registrado apenas como legado/provisÃ³rio.

## O que jÃ¡ foi validado

- O fluxo mock do projeto segue funcionando.
- O `.env` local estÃ¡ ignorado pelo Git e nÃ£o deve ser versionado.
- A trava `ENABLE_REAL_HTTP` existe e bloqueia chamadas reais por padrÃ£o.
- A trava `ENABLE_REAL_PUBLISH` deve permanecer desligada.
- O preview seguro do request GraphQL mascara o header `Authorization`.
- O provider Shopee ja monta `POST` GraphQL assinado para `shopOfferV2`.
- O mapper GraphQL normaliza `nodes` para `Offer` sem inventar preco quando a API nao retornar preco de produto.
- O mock usa payload fake no formato `ShopeeOfferConnectionV2`, mantendo paridade de desenvolvimento com o caminho real.
- O fluxo de copy, compliance, elegibilidade de grupo e revisao aceita preco desconhecido (`0`) como consultar valor atualizado no link.
- A base URL real usada nos testes manuais antigos foi `https://partner.shopeemobile.com`.
- O path legado em anÃ¡lise foi `/api/v2/product/search_item`.
- O endpoint respondeu quando chamado sem query, indicando ausÃªncia de `partner_id`.
- O cÃ³digo passou a validar que `SHOPEE_PARTNER_ID` precisa ser numÃ©rico.
- O cÃ³digo passou a rejeitar payloads de erro da Shopee em vez de normalizar `0` ofertas silenciosamente.
- Foi criada ferramenta para capturar resposta real jÃ¡ anonimizada em `tmp/`.
- A Open API correta validada em chamada real usa GraphQL com a query
  `shopOfferV2`.
- A documentacao operacional agora distingue tres contratos: `shopOfferV2`
  para lojas, `shopeeOfferV2` para oferta/listagem antiga e `productOfferV2`
  para itens/produtos.
- O fluxo de feed em lote tambem fica registrado com `listItemFeeds` para
  descoberta de feeds e `getItemFeedData` para download paginado dos dados.

## Contrato GraphQL informado

Query:

```text
shopOfferV2
```

Endpoint informado:

```text
POST https://open-api.affiliate.shopee.com.br/graphql
```

Headers conhecidos:

```text
Authorization: SHA256 Credential=<credential>, Signature=<signature>, Timestamp=<timestamp>
Content-Type: application/json
```

Assinatura:

```text
Signature = SHA256(Credential + Timestamp + Payload + Secret)
```

`Payload` Ã© o body JSON exato enviado na requisiÃ§Ã£o. A mÃ¡quina precisa manter
horÃ¡rio correto, porque a diferenÃ§a entre `Timestamp` e o servidor nÃ£o pode
exceder 10 minutos.

AlÃ©m da listagem de ofertas, a Open API informada possui operaÃ§Ãµes para marca,
produto, product feed, brand feed e geraÃ§Ã£o de short URL.

Formato do body:

```json
{
  "query": "...",
  "operationName": "...",
  "variables": {
    "myVariable": "someValue"
  }
}
```

Envelope de resposta:

```json
{
  "data": {},
  "errors": []
}
```

Quando nÃ£o houver erro, `errors` pode nÃ£o ser retornado.

Retorno:

```text
ShopOfferConnectionV2!
```

ParÃ¢metros:

| Campo | Tipo | DescriÃ§Ã£o |
| --- | --- | --- |
| `keyword` | `String` | Busca por nome da loja. |
| `shopType` | `Int[]` | Filtra tipo de loja. `0` all, `1` official, `2` preferred, `3` cross border. |
| `sortType` | `Int` | `1` mais recentes, `2` maior comissao, `3` popularidade. |
| `sellerCommCoveRatio` | `String` | Proporcao de produtos da loja com seller commission. Ex.: `0.0123` para 1.23%. |
| `page` | `Int` | Numero da pagina. Padrao: `1`. |
| `limit` | `Int` | Quantidade por pagina. Padrao: `20`. |
| `shopId` | `Int64` | Busca direta por id da loja. |
| `isKeySeller` | `Boolean` | Filtro opcional para key seller. |

Resposta:

| Campo | Tipo | DescriÃ§Ã£o |
| --- | --- | --- |
| `nodes` | `[ShopOfferV2]!` | Lista de lojas/ofertas de loja. |
| `pageInfo` | `PageInfo!` | PaginaÃ§Ã£o. |

Campos de `ShopOfferV2`:

| Campo | Tipo |
| --- | --- |
| `commissionRate` | `String` |
| `imageUrl` | `String` |
| `offerLink` | `String` |
| `originalLink` | `String` |
| `shopId` | `Int64` |
| `shopName` | `String` |
| `periodStartTime` | `Int` |
| `periodEndTime` | `Int` |
| `bannerInfo` | `BannerInfo` or `null` |
| `ratingStar` | `String` |
| `shopType` | `Int[]` |
| `remainingBudget` | `Int` |
| `sellerCommCoveRatio` | `String` |

Campos de `PageInfo`:

| Campo | Tipo |
| --- | --- |
| `page` | `Int` |
| `limit` | `Int` |
| `hasNextPage` | `Bool` |
| `scrollId` | `String` or `null` |

### Erros GraphQL conhecidos

Campos esperados em `errors`:

| Campo | Tipo |
| --- | --- |
| `message` | `String` |
| `path` | `String` |
| `extensions` | `object` |
| `extensions.code` | `Int` |
| `extensions.message` | `String` |

CÃ³digos conhecidos:

| CÃ³digo | Significado |
| --- | --- |
| `10000` | System error |
| `10010` | Request parsing error |
| `10020` | Identity authentication error |
| `10030` | Trigger traffic limiting |
| `11000` | Business processing error |

### MutaÃ§Ã£o `generateShortLink`

A mutaÃ§Ã£o de short URL deve ser considerada importante para o fluxo de envio,
pois permite gerar links curtos rastreÃ¡veis para as mensagens.

Exemplo informado:

```graphql
mutation {
  generateShortLink(
    input: {
      originUrl: "https://shopee.com.br/Apple-Iphone-11-128GB-Local-Set-i.52377417.6309028319"
      subIds: ["s1", "s2", "s3", "s4", "s5"]
    }
  ) {
    shortLink
  }
}
```

Uso esperado:

- receber `originUrl` de oferta, produto ou cupom;
- gerar `subIds` internos para rastrear grupo, campanha, execuÃ§Ã£o e origem;
- salvar `shortLink` junto da oferta selecionada;
- usar `shortLink` nas mensagens aprovadas.

## Contrato adicional documentado: `productOfferV2`

Este contrato fica registrado como busca por item/produto, separado do fluxo
de loja validado em `shopOfferV2`.

Query:

```text
productOfferV2
```

Objetivo:

- buscar itens/ofertas por nome de produto;
- navegar listas por `listType` e `matchId`;
- ordenar por `sortType`.

ParÃ¢metros:

| Campo | Tipo | DescriÃ§Ã£o |
| --- | --- | --- |
| `listType` | `Int` | Tipo da lista. `0` all, `1` highest commission, `2` top performing, `3` landing category, `4` detail category, `5` detail shop, `6` detail collection. Padrao: `0`. |
| `matchId` | `Int64` | Categoria para `LANDING_CATEGORY` e `DETAIL_CATEGORY`; loja para `DETAIL_SHOP`; colecao para `DETAIL_COLLECTION`. |
| `keyword` | `String` | Busca por nome do produto. |
| `sortType` | `Int` | `1` relevance, `2` sold desc, `3` price desc, `4` price asc, `5` commission desc. |
| `page` | `Int` | Numero da pagina. Padrao: `1`. |
| `limit` | `Int` | Quantidade por pagina. Padrao: `20`. |
| `itemId` | `Int64` | Id do item. |
| `shopId` | `Int64` | Id da loja. |
| `productCatId` | `Int` | Id da categoria do produto. |
| `isAMSOffer` | `Boolean` | Filtro de AMS offer. |
| `isKeySeller` | `Boolean` | Filtro opcional para key seller. |

ObservaÃ§Ã£o operacional:

- `productOfferV2` ainda nao foi validada por chamada real neste projeto;
- o contrato atual validado em execucao continua sendo `shopOfferV2`;
- qualquer troca do provider principal para `productOfferV2` exige preview,
  chamada controlada e captura de resposta real antes de consolidar.

Campos de resposta obrigatorios de `ProductOfferV2`:

| Campo | Tipo | Observacao |
| --- | --- | --- |
| `itemId` | `Int64` | item id |
| `commissionRate` | `String` | taxa geral de comissao |
| `appExistRate` | `String` | taxa para usuario recorrente no app |
| `appNewRate` | `String` | taxa para usuario novo no app |
| `webExistRate` | `String` | taxa para usuario recorrente no web |
| `webNewRate` | `String` | taxa para usuario novo no web |
| `commission` | `String` | valor da comissao |
| `price` | `String` | preco do produto |
| `sales` | `Int64` | quantidade de vendas |
| `imageUrl` | `String` | url da imagem |
| `productName` | `String` | nome do produto |
| `shopName` | `String` | nome da loja |
| `productLink` | `String` | link do produto |
| `offerLink` | `String` | link de afiliado/oferta |
| `periodEndTime` | `Int64` | fim da oferta |
| `periodStartTime` | `Int64` | inicio da oferta |
| `priceMin` | `String` | preco minimo |
| `priceMax` | `String` | preco maximo |
| `productCatIds` | `[Int!]` | categorias l1-l3 |
| `ratingStar` | `String` | nota do produto |
| `priceDiscountRate` | `Int` | desconto de 0 a 100 |
| `shopId` | `Int64` | id da loja |
| `shopType` | `[Int!]` | tipo da loja |
| `sellerCommissionRate` | `String` | seller commission rate |
| `shopeeCommissionRate` | `String` | shopee commission rate |

Campos de `PageInfo` para `productOfferV2`:

| Campo | Tipo | Observacao |
| --- | --- | --- |
| `page` | `Int` | numero da pagina |
| `limit` | `Int` | quantidade por pagina |
| `hasNextPage` | `Boolean` | indica proxima pagina |
| `scrollId` | `String` | cursor opcional com expiraÃ§Ã£o curta |

Decisao operacional atual:

- quando a equipe exportar ou auditar `productOfferV2`, deve preservar todos os
  campos acima;
- o builder do projeto passa a solicitar todos esses campos na query;
- CSVs e artefatos de inspecao dessa query nao devem reduzir o contrato sem
  motivo explicito.
- nomes internos de cenarios, perfis ou metodos do projeto nao devem substituir
  os nomes da API na documentacao tecnica.

## Contrato adicional documentado: `listItemFeeds`

Este contrato fica registrado como discovery de feeds disponiveis para download
em massa, antes da chamada de dados paginados.

Query:

```text
listItemFeeds
```

Objetivo:

- descobrir feeds disponiveis antes do download;
- listar metadados como id, data, total de registros e modo do feed;
- preparar a chamada seguinte de `getItemFeedData`.

ParÃ¢metros:

| Campo | Tipo | DescriÃ§Ã£o |
| --- | --- | --- |
| `feedMode` | `FeedMode` | Filtro opcional por `FULL` ou `DELTA`. Sem valor, retorna todos os feeds disponiveis. |

ObservaÃ§Ã£o operacional:

- usar `listItemFeeds` antes de `getItemFeedData`;
- o retorno esperado inclui metadados suficientes para montar o `datafeedId`;
- este contrato ainda nao foi validado por chamada real neste projeto.

## Contrato adicional documentado: `getItemFeedData`

Este contrato fica registrado como download paginado dos dados reais do feed.

Query:

```text
getItemFeedData
```

Objetivo:

- baixar registros reais de produto a partir de um feed descoberto;
- suportar FULL sync com dataset completo;
- suportar DELTA sync com mudancas incrementais por item.

ParÃ¢metros:

| Campo | Tipo | DescriÃ§Ã£o |
| --- | --- | --- |
| `datafeedId` | `String` | Obrigatorio. Id composto vindo de `listItemFeeds`, no formato `{datafeedId}_{feedMode}_{grassDate}`. |
| `offset` | `Int` | Offset da pagina, com inicio em `0`. Padrao: `0`. |
| `limit` | `Int` | Quantidade de registros por pagina. Padrao: `500`. Maximo: `500`. |

ObservaÃ§Ã£o operacional:

- `getItemFeedData` depende de `datafeedId` retornado por `listItemFeeds`;
- em modo `DELTA`, cada linha pode trazer `updateType` com `NEW`, `UPDATE`
  ou `DELETE`;
- este contrato ainda nao foi validado por chamada real neste projeto.

## EvidÃªncias observadas

### Status seguro e preview GraphQL em 2026-06-25

Com credenciais configuradas somente no `.env` local, o status seguro foi
aprovado sem expor `partner_id`, `tracking_id` ou `secret_key`:

```text
INFO | enable_real_http=true
INFO | enable_real_publish=false
INFO | default_dry_run=true
INFO | graphql_url=https://open-api.affiliate.shopee.com.br/graphql
INFO | Ambiente pronto para chamada real controlada
```

O preview seguro do provider Shopee tambem foi aprovado sem executar HTTP real:

```text
INFO | method=POST
INFO | url=https://open-api.affiliate.shopee.com.br/graphql
INFO | header.Authorization=<masked:126 chars>
INFO | header.Content-Type=application/json
INFO | body.operationName=ShopOfferList
INFO | body.variables.keyword=mae bebe
INFO | body.variables.limit=1
INFO | body.variables.page=1
INFO | Nenhuma chamada HTTP foi executada.
```

Proxima etapa: executar uma unica chamada real controlada com `--limit 1`,
somente apos aprovacao humana explicita.

### Resposta real validada para `shopOfferV2`

Uma chamada real controlada com `keyword="mae bebe"` confirmou:

- `data.shopOfferV2` como campo-raiz correto;
- `shopName` no lugar de `offerName`;
- `shopId` numerico e `originalLink` apontando para `/shop/<id>`;
- `pageInfo.scrollId` presente e `hasNextPage=false` com `limit=20`;
- ausencia de `errors` no envelope GraphQL.

### Endpoint sem query

Resposta observada ao acessar o endpoint sem parÃ¢metros:

```json
{
  "error": "error_param",
  "message": "There is no partner_id in query."
}
```

InterpretaÃ§Ã£o: o host/path responde, mas exige parÃ¢metros assinados.

### Partner id invÃ¡lido

Resposta observada com valor de `SHOPEE_PARTNER_ID` nÃ£o numÃ©rico ou fora do formato aceito:

```json
{
  "error": "error_param",
  "message": "Partner_id is invalid, should be an integer between 0 and 4294967295."
}
```

InterpretaÃ§Ã£o: `SHOPEE_PARTNER_ID` deve ser somente numÃ©rico.

### Timestamp expirado

Resposta observada antes de sincronizar o relÃ³gio local:

```text
Shopee response returned error=error_param: Timestamp is expired.
```

InterpretaÃ§Ã£o: o relÃ³gio local precisava de sincronizaÃ§Ã£o. ApÃ³s ajuste do Windows Time Service, o erro evoluiu para HTTP 403, indicando que o timestamp deixou de ser o bloqueio principal.

### HTTP 403

Resposta observada apÃ³s corrigir relÃ³gio e validar `partner_id` numÃ©rico:

```text
Shopee request failed with status=403
```

InterpretaÃ§Ã£o atual: bloqueio provÃ¡vel de autorizaÃ§Ã£o, permissÃ£o, assinatura, app ainda em anÃ¡lise, endpoint nÃ£o liberado para a conta ou credenciais incompatÃ­veis com o app/endpoint.

## ConfiguraÃ§Ã£o local esperada para retomada

Nunca versionar valores reais. Manter no `.env` local:

```text
ENABLE_REAL_HTTP=true
ENABLE_REAL_PUBLISH=false
SHOPEE_PARTNER_ID=<id_numerico_real>
SHOPEE_SECRET_KEY=<secret_key_real>
SHOPEE_TRACKING_ID=<tracking_id_se_aplicavel>
```

E, na sessÃ£o do PowerShell usada para os comandos reais:

```powershell
$env:SHOPEE_GRAPHQL_URL="https://open-api.affiliate.shopee.com.br/graphql"
```

## Comandos para retomar quando a conta for aprovada

1. Atualizar repositÃ³rio e rodar qualidade:

```powershell
cd C:\Automacao_Grupos-de-Ofertas
git pull
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

2. Validar variÃ¡veis sem expor segredo:

```powershell
.\.venv\Scripts\python.exe -c "from ofertas_bot.settings import get_settings; s=get_settings(); v=s.shopee_partner_id or ''; k=s.shopee_secret_key or ''; t=s.shopee_tracking_id or ''; print('partner_numeric=', v.isdecimal(), 'partner_len=', len(v)); print('secret_len=', len(k)); print('tracking_len=', len(t))"
```

3. Reconfigurar variÃ¡veis de sessÃ£o:

```powershell
$env:SHOPEE_GRAPHQL_URL="https://open-api.affiliate.shopee.com.br/graphql"
```

4. Rodar status seguro:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.safe_status --marketplace shopee
```

Resultado esperado antes de qualquer chamada real:

```text
INFO | Ambiente pronto para chamada real controlada
INFO | PublicaÃ§Ã£o real continua fora do escopo deste status.
```

5. Revisar o preview seguro do provider Shopee GraphQL antes de rodar chamada real.

O provider ja monta um `POST` GraphQL para `shopOfferV2`, normaliza `nodes`
para `Offer` e usa `pageInfo.hasNextPage` para paginacao. O ponto pendente
e validar esse contrato contra uma resposta real da conta aprovada.

6. Rodar preview seguro apÃ³s a refatoraÃ§Ã£o:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

7. Conferir no painel/documentaÃ§Ã£o oficial da conta aprovada:

- endpoint GraphQL;
- headers obrigatÃ³rios;
- formato de assinatura/autenticaÃ§Ã£o;
- envelope de resposta;
- query de cupons, se existir;
- queries de marca, produto, product feed e brand feed;
- mutaÃ§Ã£o `generateShortLink`;
- limites e formato de `subIds`;
- se `offerLink` jÃ¡ contÃ©m tracking de afiliado.

8. Fazer uma Ãºnica chamada real controlada:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --execute-real-http-once
```

## O que nÃ£o fazer enquanto a conta estiver em anÃ¡lise

- NÃ£o repetir chamadas reais em loop.
- NÃ£o ativar publicaÃ§Ã£o real.
- NÃ£o salvar payload bruto.
- NÃ£o commitar `.env`.
- NÃ£o colar `SHOPEE_SECRET_KEY`, assinatura, tokens ou URL assinada em chat, issue ou commit.
- NÃ£o marcar a integraÃ§Ã£o como concluÃ­da enquanto o HTTP 403 nÃ£o for explicado.

## CritÃ©rio para considerar esta etapa concluÃ­da

A integraÃ§Ã£o Shopee sÃ³ deve sair de `pausado` quando:

1. a conta/app Shopee estiver aprovada;
2. o endpoint GraphQL real estiver confirmado no painel/documentaÃ§Ã£o oficial;
3. autenticaÃ§Ã£o e headers estiverem compatÃ­veis com o contrato oficial;
4. `ShopeeProvider`, gateway e mapper estiverem refatorados para `shopOfferV2`;
5. uma chamada real controlada com `--limit 1` retornar pelo menos uma resposta vÃ¡lida ou um payload vazio documentado como vÃ¡lido;
6. a resposta real for anonimizada antes de virar fixture;
7. `ruff` e `pytest` passarem sem erros;
8. `ENABLE_REAL_PUBLISH` continuar `false`.

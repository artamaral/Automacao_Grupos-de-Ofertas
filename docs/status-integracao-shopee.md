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
- O provider Shopee ja monta `POST` GraphQL assinado para `shopeeOfferV2`.
- O mapper GraphQL normaliza `nodes` para `Offer` sem inventar preco quando a API nao retornar preco de produto.
- O mock usa payload fake no formato `ShopeeOfferConnectionV2`, mantendo paridade de desenvolvimento com o caminho real.
- O fluxo de copy, compliance, elegibilidade de grupo e revisao aceita preco desconhecido (`0`) como consultar valor atualizado no link.
- A base URL real usada nos testes manuais antigos foi `https://partner.shopeemobile.com`.
- O path legado em anÃ¡lise foi `/api/v2/product/search_item`.
- O endpoint respondeu quando chamado sem query, indicando ausÃªncia de `partner_id`.
- O cÃ³digo passou a validar que `SHOPEE_PARTNER_ID` precisa ser numÃ©rico.
- O cÃ³digo passou a rejeitar payloads de erro da Shopee em vez de normalizar `0` ofertas silenciosamente.
- Foi criada ferramenta para capturar resposta real jÃ¡ anonimizada em `tmp/`.
- A Open API correta informada para ofertas usa GraphQL com a query
  `shopeeOfferV2`.

## Contrato GraphQL informado

Query:

```text
shopeeOfferV2
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
ShopeeOfferConnectionV2!
```

ParÃ¢metros:

| Campo | Tipo | DescriÃ§Ã£o |
| --- | --- | --- |
| `keyword` | `String` | Busca por nome da oferta. |
| `sortType` | `Int` | `1` mais recentes, `2` maior comissÃ£o. |
| `page` | `Int` | NÃºmero da pÃ¡gina. |
| `limit` | `Int` | Quantidade por pÃ¡gina. |

Resposta:

| Campo | Tipo | DescriÃ§Ã£o |
| --- | --- | --- |
| `nodes` | `[ShopeeOfferV2]!` | Lista de ofertas. |
| `pageInfo` | `PageInfo!` | PaginaÃ§Ã£o. |

Campos de `ShopeeOfferV2`:

| Campo | Tipo |
| --- | --- |
| `commissionRate` | `String` |
| `imageUrl` | `String` |
| `offerLink` | `String` |
| `originalLink` | `String` |
| `offerName` | `String` |
| `offerType` | `Int` |
| `categoryId` | `Int64` |
| `collectionId` | `Int64` |
| `periodStartTime` | `Int` |
| `periodEndTime` | `Int` |

Campos de `PageInfo`:

| Campo | Tipo |
| --- | --- |
| `page` | `Int` |
| `limit` | `Int` |
| `hasNextPage` | `Bool` |

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

## EvidÃªncias observadas

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

O provider ja monta um `POST` GraphQL para `shopeeOfferV2`, normaliza `nodes`
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
4. `ShopeeProvider`, gateway e mapper estiverem refatorados para `shopeeOfferV2`;
5. uma chamada real controlada com `--limit 1` retornar pelo menos uma resposta vÃ¡lida ou um payload vazio documentado como vÃ¡lido;
6. a resposta real for anonimizada antes de virar fixture;
7. `ruff` e `pytest` passarem sem erros;
8. `ENABLE_REAL_PUBLISH` continuar `false`.

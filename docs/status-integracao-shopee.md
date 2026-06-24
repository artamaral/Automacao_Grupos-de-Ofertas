# Status da integração Shopee

Este arquivo registra o ponto exato em que a integração real com a Shopee foi pausada, para retomada futura sem perda de contexto.

## Status atual

**Status:** contrato real identificado como GraphQL, aguardando refatoração do
provider Shopee antes de qualquer chamada real.

A conta Shopee e a Open API de afiliados devem ser tratadas pelo contrato
GraphQL informado para o projeto. O contrato REST usado antes no código fica
registrado apenas como legado/provisório.

## O que já foi validado

- O fluxo mock do projeto segue funcionando.
- O `.env` local está ignorado pelo Git e não deve ser versionado.
- A trava `ENABLE_REAL_HTTP` existe e bloqueia chamadas reais por padrão.
- A trava `ENABLE_REAL_PUBLISH` deve permanecer desligada.
- O `safe_status` valida pré-requisitos antes de qualquer chamada real.
- O preview seguro do request mascara `partner_id` e `sign`.
- A base URL real usada nos testes manuais antigos foi `https://partner.shopeemobile.com`.
- O path legado em análise foi `/api/v2/product/search_item`.
- O endpoint respondeu quando chamado sem query, indicando ausência de `partner_id`.
- O código passou a validar que `SHOPEE_PARTNER_ID` precisa ser numérico.
- O código passou a rejeitar payloads de erro da Shopee em vez de normalizar `0` ofertas silenciosamente.
- Foi criada ferramenta para capturar resposta real já anonimizada em `tmp/`.
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

`Payload` é o body JSON exato enviado na requisição. A máquina precisa manter
horário correto, porque a diferença entre `Timestamp` e o servidor não pode
exceder 10 minutos.

Além da listagem de ofertas, a Open API informada possui operações para marca,
produto, product feed, brand feed e geração de short URL.

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

Quando não houver erro, `errors` pode não ser retornado.

Retorno:

```text
ShopeeOfferConnectionV2!
```

Parâmetros:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `keyword` | `String` | Busca por nome da oferta. |
| `sortType` | `Int` | `1` mais recentes, `2` maior comissão. |
| `page` | `Int` | Número da página. |
| `limit` | `Int` | Quantidade por página. |

Resposta:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `nodes` | `[ShopeeOfferV2]!` | Lista de ofertas. |
| `pageInfo` | `PageInfo!` | Paginação. |

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

Códigos conhecidos:

| Código | Significado |
| --- | --- |
| `10000` | System error |
| `10010` | Request parsing error |
| `10020` | Identity authentication error |
| `10030` | Trigger traffic limiting |
| `11000` | Business processing error |

### Mutação `generateShortLink`

A mutação de short URL deve ser considerada importante para o fluxo de envio,
pois permite gerar links curtos rastreáveis para as mensagens.

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
- gerar `subIds` internos para rastrear grupo, campanha, execução e origem;
- salvar `shortLink` junto da oferta selecionada;
- usar `shortLink` nas mensagens aprovadas.

## Evidências observadas

### Endpoint sem query

Resposta observada ao acessar o endpoint sem parâmetros:

```json
{
  "error": "error_param",
  "message": "There is no partner_id in query."
}
```

Interpretação: o host/path responde, mas exige parâmetros assinados.

### Partner id inválido

Resposta observada com valor de `SHOPEE_PARTNER_ID` não numérico ou fora do formato aceito:

```json
{
  "error": "error_param",
  "message": "Partner_id is invalid, should be an integer between 0 and 4294967295."
}
```

Interpretação: `SHOPEE_PARTNER_ID` deve ser somente numérico.

### Timestamp expirado

Resposta observada antes de sincronizar o relógio local:

```text
Shopee response returned error=error_param: Timestamp is expired.
```

Interpretação: o relógio local precisava de sincronização. Após ajuste do Windows Time Service, o erro evoluiu para HTTP 403, indicando que o timestamp deixou de ser o bloqueio principal.

### HTTP 403

Resposta observada após corrigir relógio e validar `partner_id` numérico:

```text
Shopee request failed with status=403
```

Interpretação atual: bloqueio provável de autorização, permissão, assinatura, app ainda em análise, endpoint não liberado para a conta ou credenciais incompatíveis com o app/endpoint.

## Configuração local esperada para retomada

Nunca versionar valores reais. Manter no `.env` local:

```text
ENABLE_REAL_HTTP=true
ENABLE_REAL_PUBLISH=false
SHOPEE_PARTNER_ID=<id_numerico_real>
SHOPEE_SECRET_KEY=<secret_key_real>
SHOPEE_TRACKING_ID=<tracking_id_se_aplicavel>
```

E, na sessão do PowerShell usada para os comandos reais:

```powershell
$env:SHOPEE_GRAPHQL_URL="https://open-api.affiliate.shopee.com.br/graphql"
```

## Comandos para retomar quando a conta for aprovada

1. Atualizar repositório e rodar qualidade:

```powershell
cd C:\Automacao_Grupos-de-Ofertas
git pull
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

2. Validar variáveis sem expor segredo:

```powershell
.\.venv\Scripts\python.exe -c "from ofertas_bot.settings import get_settings; s=get_settings(); v=s.shopee_partner_id or ''; k=s.shopee_secret_key or ''; t=s.shopee_tracking_id or ''; print('partner_numeric=', v.isdecimal(), 'partner_len=', len(v)); print('secret_len=', len(k)); print('tracking_len=', len(t))"
```

3. Reconfigurar variáveis de sessão:

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
INFO | Publicação real continua fora do escopo deste status.
```

5. Refatorar o provider Shopee para GraphQL antes de rodar preview ou chamada real.

O provider deve montar um `POST` GraphQL para `shopeeOfferV2`, normalizar
`nodes` para `Offer` e usar `pageInfo.hasNextPage` para paginação.

6. Rodar preview seguro após a refatoração:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

7. Conferir no painel/documentação oficial da conta aprovada:

- endpoint GraphQL;
- headers obrigatórios;
- formato de assinatura/autenticação;
- envelope de resposta;
- query de cupons, se existir;
- queries de marca, produto, product feed e brand feed;
- mutação `generateShortLink`;
- limites e formato de `subIds`;
- se `offerLink` já contém tracking de afiliado.

8. Fazer uma única chamada real controlada:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --execute-real-http-once
```

## O que não fazer enquanto a conta estiver em análise

- Não repetir chamadas reais em loop.
- Não ativar publicação real.
- Não salvar payload bruto.
- Não commitar `.env`.
- Não colar `SHOPEE_SECRET_KEY`, assinatura, tokens ou URL assinada em chat, issue ou commit.
- Não marcar a integração como concluída enquanto o HTTP 403 não for explicado.

## Critério para considerar esta etapa concluída

A integração Shopee só deve sair de `pausado` quando:

1. a conta/app Shopee estiver aprovada;
2. o endpoint GraphQL real estiver confirmado no painel/documentação oficial;
3. autenticação e headers estiverem compatíveis com o contrato oficial;
4. `ShopeeProvider`, gateway e mapper estiverem refatorados para `shopeeOfferV2`;
5. uma chamada real controlada com `--limit 1` retornar pelo menos uma resposta válida ou um payload vazio documentado como válido;
6. a resposta real for anonimizada antes de virar fixture;
7. `ruff` e `pytest` passarem sem erros;
8. `ENABLE_REAL_PUBLISH` continuar `false`.

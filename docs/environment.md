# VariÃ¡veis de ambiente e execuÃ§Ã£o local segura

Este documento descreve as variÃ¡veis usadas pelo projeto e exemplos seguros de execuÃ§Ã£o local.

A regra principal Ã©: por padrÃ£o, o projeto deve rodar em `mock`, com `dry-run` ativo, sem HTTP real e sem publicaÃ§Ã£o real.

## Como preparar o `.env`

Copie o arquivo de exemplo:

```powershell
Copy-Item .env.example .env
```

Edite apenas o `.env` local. Nunca edite `.env.example` com valores reais.

O arquivo `.env` nÃ£o deve ser versionado.

Confirme que ele estÃ¡ ignorado pelo Git:

```powershell
git check-ignore -v .env
```

A saÃ­da esperada deve apontar para a regra `.env` no `.gitignore`.

## ObservaÃ§Ã£o sobre variÃ¡veis externas

As variÃ¡veis principais do `Settings` sÃ£o carregadas do `.env` local.

As configuracoes externas dos providers sao lidas do ambiente da sessao de execucao. Para Shopee, o caminho operacional atual usa GraphQL; as variaveis REST antigas existem apenas para codigo legado e testes de compatibilidade.

Exemplo seguro para a sessao atual:

```powershell
$env:SHOPEE_GRAPHQL_URL="https://open-api.affiliate.shopee.com.br/graphql"
```

A Open API de afiliados informada para a Shopee usa GraphQL. A query de lista de ofertas e `shopeeOfferV2`, e a mutacao `generateShortLink` deve ser usada para gerar links curtos rastreaveis.

## VariÃ¡veis gerais

| VariÃ¡vel | PadrÃ£o | DescriÃ§Ã£o |
| --- | --- | --- |
| `APP_ENV` | `local` | Ambiente lÃ³gico da execuÃ§Ã£o. |
| `LOG_LEVEL` | `INFO` | NÃ­vel de log planejado para execuÃ§Ã£o local. |
| `DEFAULT_DRY_RUN` | `true` | MantÃ©m publicaÃ§Ã£o simulada por padrÃ£o. |
| `MAX_OFFERS_PER_RUN` | `5` | Limite padrÃ£o de ofertas por execuÃ§Ã£o. |
| `ENABLE_REAL_HTTP` | `false` | Trava para chamadas HTTP reais. Deve permanecer desligada atÃ© o checklist permitir. |
| `ENABLE_REAL_PUBLISH` | `false` | Trava para publicaÃ§Ã£o real. Deve permanecer desligada. |

## Shopee

| VariÃ¡vel | ObrigatÃ³ria para provider Shopee | DescriÃ§Ã£o |
| --- | --- | --- |
| `SHOPEE_PARTNER_ID` | Sim | Identificador numÃ©rico do parceiro. Deve conter apenas dÃ­gitos e estar no intervalo aceito pela API. |
| `SHOPEE_SECRET_KEY` | Sim | Chave usada para assinatura. NÃ£o imprimir em logs. |
| `SHOPEE_TRACKING_ID` | Nao | Identificador de rastreio de afiliado, quando aplicavel. |
| `SHOPEE_GRAPHQL_URL` | Nao | Endpoint GraphQL da Open API de afiliados. Padrao: `https://open-api.affiliate.shopee.com.br/graphql`. |
| `SHOPEE_BASE_URL` | Nao | Legado REST. Nao usado no fluxo principal Shopee GraphQL. |
| `SHOPEE_SEARCH_PATH` | Nao | Legado REST. Nao usado no fluxo principal Shopee GraphQL. |
| `SHOPEE_SEARCH_PATH_CONFIRMED` | Nao | Legado REST. Nao e mais trava do fluxo principal GraphQL. |

Estado atual:

- provider valida configuracao;
- partner id da Shopee e validado como numerico antes da chamada real;
- gateway GraphQL monta `POST` assinado para `shopeeOfferV2`;
- preview seguro mascara o header `Authorization`;
- mock usa payload fake no formato `ShopeeOfferConnectionV2`, em paridade com o caminho real;
- mapper GraphQL normaliza `nodes` para `Offer` sem inventar preco quando a API nao retornar preco;
- chamada real continua desativada por padrao via `ENABLE_REAL_HTTP=false`;
- payload real ainda nao deve ser usado sem anonimizacao;
- short links devem ser gerados pela mutacao `generateShortLink`.

## Amazon

| VariÃ¡vel | ObrigatÃ³ria para provider Amazon | DescriÃ§Ã£o |
| --- | --- | --- |
| `AMAZON_ACCESS_KEY` | Sim | Identificador de acesso da PA API. NÃ£o imprimir em logs. |
| `AMAZON_SECRET_KEY` | Sim | Chave usada para autenticaÃ§Ã£o. NÃ£o imprimir em logs. |
| `AMAZON_PARTNER_TAG` | Sim | Tag de associado. |
| `AMAZON_REGION` | NÃ£o | RegiÃ£o lÃ³gica. PadrÃ£o atual: `BR`. |
| `AMAZON_BASE_URL` | NÃ£o | Base URL usada pelo builder. PadrÃ£o seguro: `https://example.com`. |
| `AMAZON_SEARCH_PATH` | NÃ£o | Caminho do endpoint de busca. PadrÃ£o atual: `/paapi5/searchitems`. Revisar a decisÃ£o PA-API 5.0 versus Creators API antes de chamada real. |

Estado atual:

- provider valida configuraÃ§Ã£o;
- gateway fake/injetÃ¡vel funciona em teste;
- base URL Ã© configurÃ¡vel sem ativar HTTP real;
- path de busca Ã© configurÃ¡vel fora do Git;
- chamada real continua desativada por padrÃ£o;
- assinatura real da PA API ainda nÃ£o foi implementada;
- contrato final da Amazon depende da decisÃ£o PA-API 5.0 versus Creators API;
- uso oficial da Amazon pode depender de elegibilidade da conta na Creators API,
  incluindo conta de criador aprovada e volume mÃ­nimo recente de vendas
  qualificadas;
- enquanto nÃ£o houver elegibilidade, Amazon deve operar apenas em modo
  mock/fake, entrada manual/curada ou experimento de scraping explicitamente
  aprovado e isolado.

## ExecuÃ§Ã£o segura recomendada

### Rodar pipeline completo com mock

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace mock --niche maquiagem --limit 2
```

Esse Ã© o caminho mais seguro para testar o fluxo completo.

### Validar erro amigÃ¡vel da Shopee sem credenciais

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 2
```

Se o `.env` nÃ£o tiver as variÃ¡veis da Shopee, o CLI deve mostrar erro amigÃ¡vel e exit code `2`.

### Validar erro amigÃ¡vel da Amazon sem credenciais

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace amazon --niche casa --limit 2
```

Se o `.env` nÃ£o tiver as variÃ¡veis da Amazon, o CLI deve mostrar erro amigÃ¡vel e exit code `2`.

### Status seguro da Shopee antes de chamada real

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.safe_status --marketplace shopee
```

Use esse comando para conferir se o ambiente estÃ¡ pronto ou bloqueado antes de qualquer chamada real controlada.

### Preview seguro da Shopee antes de chamada real

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

Use esse comando para revisar metodo, URL GraphQL, header `Authorization` mascarado e variaveis nao sensiveis do body antes de uma chamada real controlada.

### Chamada real controlada da Shopee

Antes de rodar `--execute-real-http-once`, o ambiente local precisa ter `ENABLE_REAL_HTTP=true`, credenciais Shopee aprovadas no `.env` local e, se necessario, `SHOPEE_GRAPHQL_URL` apontando para o endpoint oficial. `ENABLE_REAL_PUBLISH` deve continuar `false`.

## Testes locais

Use sempre:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

Os testes de provider usam transport fake e nÃ£o acessam internet.

## O que nÃ£o fazer

- NÃ£o colocar valores reais no `.env.example`.
- NÃ£o commitar `.env`.
- NÃ£o imprimir chaves, tokens, cookies, QR code ou sessÃµes.
- NÃ£o ativar `ENABLE_REAL_HTTP=true` antes do checklist de produÃ§Ã£o.
- NÃ£o ativar `ENABLE_REAL_PUBLISH=true` antes de revisÃ£o manual completa.
- NÃ£o usar payload real em teste sem anonimizaÃ§Ã£o.
- NÃ£o executar chamada real se o endpoint oficial nÃ£o foi confirmado.

## Ordem segura para evoluir

1. Testar sempre com `mock`.
2. Testar providers com `StaticHttpTransport`.
3. Validar payloads reais apenas como fixtures anonimizadas.
4. Confirmar contratos oficiais dos marketplaces.
5. Concluir checklist de produÃ§Ã£o.
6. SÃ³ depois conectar `ENABLE_REAL_HTTP` ao transport real.
7. Manter publicaÃ§Ã£o real desligada atÃ© revisÃ£o manual final.

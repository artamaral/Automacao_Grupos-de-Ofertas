# Variáveis de ambiente e execução local segura

Este documento descreve as variáveis usadas pelo projeto e exemplos seguros de execução local.

A regra principal é: por padrão, o projeto deve rodar em `mock`, com `dry-run` ativo, sem HTTP real e sem publicação real.

## Como preparar o `.env`

Copie o arquivo de exemplo:

```powershell
Copy-Item .env.example .env
```

Edite apenas o `.env` local. Nunca edite `.env.example` com valores reais.

O arquivo `.env` não deve ser versionado.

Confirme que ele está ignorado pelo Git:

```powershell
git check-ignore -v .env
```

A saída esperada deve apontar para a regra `.env` no `.gitignore`.

## Observação sobre variáveis externas

As variáveis principais do `Settings` são carregadas do `.env` local.

As configurações externas dos providers, como base URL, path e confirmação de endpoint, são lidas do ambiente da sessão de execução. Enquanto essa leitura não estiver centralizada, defina essas variáveis no PowerShell antes dos comandos de status, preview ou chamada controlada.

Exemplo seguro para a sessão atual:

```powershell
$env:SHOPEE_BASE_URL="https://partner.shopeemobile.com"
$env:SHOPEE_SEARCH_PATH="/api/v2/product/search_item"
$env:SHOPEE_SEARCH_PATH_CONFIRMED="false"
```

Use `true` em `SHOPEE_SEARCH_PATH_CONFIRMED` somente depois de confirmar o endpoint oficial e revisar o preview seguro.

## Variáveis gerais

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `APP_ENV` | `local` | Ambiente lógico da execução. |
| `LOG_LEVEL` | `INFO` | Nível de log planejado para execução local. |
| `DEFAULT_DRY_RUN` | `true` | Mantém publicação simulada por padrão. |
| `MAX_OFFERS_PER_RUN` | `5` | Limite padrão de ofertas por execução. |
| `ENABLE_REAL_HTTP` | `false` | Trava para chamadas HTTP reais. Deve permanecer desligada até o checklist permitir. |
| `ENABLE_REAL_PUBLISH` | `false` | Trava para publicação real. Deve permanecer desligada. |

## Shopee

| Variável | Obrigatória para provider Shopee | Descrição |
| --- | --- | --- |
| `SHOPEE_PARTNER_ID` | Sim | Identificador numérico do parceiro. Deve conter apenas dígitos e estar no intervalo aceito pela API. |
| `SHOPEE_SECRET_KEY` | Sim | Chave usada para assinatura. Não imprimir em logs. |
| `SHOPEE_TRACKING_ID` | Não | Identificador de rastreio de afiliado, quando aplicável. |
| `SHOPEE_BASE_URL` | Não | Base URL usada pelo builder. Padrão seguro: `https://example.com`. |
| `SHOPEE_SEARCH_PATH` | Não | Caminho do endpoint de busca/listagem. Padrão provisório: `/api/v2/product/search_item`. Confirmar no painel/documentação oficial antes de chamada real. |
| `SHOPEE_SEARCH_PATH_CONFIRMED` | Sim, para chamada real | Deve ser `true` apenas depois de comparar o preview com o endpoint oficial. Padrão seguro: `false`. |

Estado atual:

- provider valida configuração;
- partner id da Shopee é validado como numérico antes da chamada real;
- gateway fake/injetável funciona em teste;
- base URL é configurável sem ativar HTTP real;
- path de busca é configurável fora do Git;
- chamada real continua desativada por padrão;
- chamada real da Shopee exige confirmação explícita do path;
- payload real ainda não deve ser usado sem anonimização;
- endpoint da Shopee precisa de confirmação manual antes de chamada real.

## Amazon

| Variável | Obrigatória para provider Amazon | Descrição |
| --- | --- | --- |
| `AMAZON_ACCESS_KEY` | Sim | Identificador de acesso da PA API. Não imprimir em logs. |
| `AMAZON_SECRET_KEY` | Sim | Chave usada para autenticação. Não imprimir em logs. |
| `AMAZON_PARTNER_TAG` | Sim | Tag de associado. |
| `AMAZON_REGION` | Não | Região lógica. Padrão atual: `BR`. |
| `AMAZON_BASE_URL` | Não | Base URL usada pelo builder. Padrão seguro: `https://example.com`. |
| `AMAZON_SEARCH_PATH` | Não | Caminho do endpoint de busca. Padrão atual: `/paapi5/searchitems`. Revisar a decisão PA-API 5.0 versus Creators API antes de chamada real. |

Estado atual:

- provider valida configuração;
- gateway fake/injetável funciona em teste;
- base URL é configurável sem ativar HTTP real;
- path de busca é configurável fora do Git;
- chamada real continua desativada por padrão;
- assinatura real da PA API ainda não foi implementada;
- contrato final da Amazon depende da decisão PA-API 5.0 versus Creators API.

## Execução segura recomendada

### Rodar pipeline completo com mock

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace mock --niche maquiagem --limit 2
```

Esse é o caminho mais seguro para testar o fluxo completo.

### Validar erro amigável da Shopee sem credenciais

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 2
```

Se o `.env` não tiver as variáveis da Shopee, o CLI deve mostrar erro amigável e exit code `2`.

### Validar erro amigável da Amazon sem credenciais

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace amazon --niche casa --limit 2
```

Se o `.env` não tiver as variáveis da Amazon, o CLI deve mostrar erro amigável e exit code `2`.

### Status seguro da Shopee antes de chamada real

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.safe_status --marketplace shopee
```

Use esse comando para conferir se o ambiente está pronto ou bloqueado antes de qualquer chamada real controlada.

### Preview seguro da Shopee antes de chamada real

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

Use esse comando para revisar método, base URL, path e parâmetros não sensíveis antes de uma chamada real controlada.

### Chamada real controlada da Shopee

Antes de rodar `--execute-real-http-once`, o ambiente local precisa ter:

```text
SHOPEE_SEARCH_PATH_CONFIRMED=true
```

Só defina esse valor depois de confirmar o endpoint oficial.

## Testes locais

Use sempre:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

Os testes de provider usam transport fake e não acessam internet.

## O que não fazer

- Não colocar valores reais no `.env.example`.
- Não commitar `.env`.
- Não imprimir chaves, tokens, cookies, QR code ou sessões.
- Não ativar `ENABLE_REAL_HTTP=true` antes do checklist de produção.
- Não ativar `ENABLE_REAL_PUBLISH=true` antes de revisão manual completa.
- Não usar payload real em teste sem anonimização.
- Não executar chamada real se o endpoint oficial não foi confirmado.
- Não definir `SHOPEE_SEARCH_PATH_CONFIRMED=true` sem revisão manual.

## Ordem segura para evoluir

1. Testar sempre com `mock`.
2. Testar providers com `StaticHttpTransport`.
3. Validar payloads reais apenas como fixtures anonimizadas.
4. Confirmar contratos oficiais dos marketplaces.
5. Concluir checklist de produção.
6. Só depois conectar `ENABLE_REAL_HTTP` ao transport real.
7. Manter publicação real desligada até revisão manual final.

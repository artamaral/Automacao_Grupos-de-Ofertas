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

## Variáveis gerais

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `APP_ENV` | `local` | Ambiente lógico da execução. |
| `LOG_LEVEL` | `INFO` | Nível de log planejado para execução local. |
| `DEFAULT_DRY_RUN` | `true` | Mantém publicação simulada por padrão. |
| `MAX_OFFERS_PER_RUN` | `5` | Limite padrão de ofertas por execução. |
| `ENABLE_REAL_HTTP` | `false` | Trava para futuras chamadas HTTP reais. Ainda não ativa provider real automaticamente. |
| `ENABLE_REAL_PUBLISH` | `false` | Trava para publicação real. Deve permanecer desligada. |

## Shopee

| Variável | Obrigatória para provider Shopee | Descrição |
| --- | --- | --- |
| `SHOPEE_PARTNER_ID` | Sim | Identificador do parceiro. |
| `SHOPEE_SECRET_KEY` | Sim | Chave usada para assinatura. Não imprimir em logs. |
| `SHOPEE_TRACKING_ID` | Não | Identificador de rastreio de afiliado, quando aplicável. |

Estado atual:

- provider valida configuração;
- gateway fake/injetável funciona em teste;
- chamada real continua desativada por padrão;
- payload real ainda não deve ser usado sem anonimização.

## Amazon

| Variável | Obrigatória para provider Amazon | Descrição |
| --- | --- | --- |
| `AMAZON_ACCESS_KEY` | Sim | Identificador de acesso da PA API. Não imprimir em logs. |
| `AMAZON_SECRET_KEY` | Sim | Chave usada para autenticação. Não imprimir em logs. |
| `AMAZON_PARTNER_TAG` | Sim | Tag de associado. |
| `AMAZON_REGION` | Não | Região lógica. Padrão atual: `BR`. |

Estado atual:

- provider valida configuração;
- gateway fake/injetável funciona em teste;
- chamada real continua desativada por padrão;
- assinatura real da PA API ainda não foi implementada.

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

## Ordem segura para evoluir

1. Testar sempre com `mock`.
2. Testar providers com `StaticHttpTransport`.
3. Validar payloads reais apenas como fixtures anonimizadas.
4. Concluir checklist de produção.
5. Só depois conectar `ENABLE_REAL_HTTP` ao transport real.
6. Manter publicação real desligada até revisão manual final.

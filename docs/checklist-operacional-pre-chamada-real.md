# Checklist operacional prÃ©-chamada real

## Objetivo

Consolidar a ordem final de execuÃ§Ã£o antes de qualquer chamada real controlada.

Este checklist nÃ£o libera publicaÃ§Ã£o real e nÃ£o substitui a revisÃ£o manual dos contratos oficiais dos marketplaces.

## Regra principal

Pare imediatamente se qualquer etapa falhar, divergir do esperado ou mostrar valor sensÃ­vel no terminal.

## 1. Atualizar repositÃ³rio e validar testes

```powershell
cd C:\Automacao_Grupos-de-Ofertas
git pull
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

CritÃ©rio para seguir:

- `ruff` sem erros;
- `pytest` sem erros.

## 2. Conferir contratos oficiais

Antes de configurar chamada real, revisar:

```text
docs/revisao-apis-marketplaces.md
docs/status-endpoint-shopee.md
docs/confirmacao-endpoint-shopee.md
```

CritÃ©rio para seguir:

- host/base URL confirmado;
- endpoint confirmado;
- mÃ©todo confirmado;
- parÃ¢metros obrigatÃ³rios confirmados;
- formato de assinatura confirmado;
- formato de resposta esperado compreendido.

## 3. Configurar `.env` local

Configurar apenas no ambiente local:

```text
ENABLE_REAL_HTTP=true
ENABLE_REAL_PUBLISH=false
SHOPEE_GRAPHQL_URL=https://open-api.affiliate.shopee.com.br/graphql
```

Credenciais reais ficam somente no `.env` local: `SHOPEE_PARTNER_ID`, `SHOPEE_SECRET_KEY` e, se aplicavel, `SHOPEE_TRACKING_ID`.

Criterio para seguir:

- `.env` nao versionado;
- publicacao real desligada;
- endpoint GraphQL oficial conferido;
- nenhum valor real copiado para arquivos versionados.

## 4. Rodar diagnÃ³stico de HTTP real

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --diagnose-real-http
```

CritÃ©rio para seguir:

```text
INFO | DiagnÃ³stico de HTTP real aprovado para marketplace=shopee
INFO | Nenhuma chamada HTTP foi executada.
INFO | Nenhuma publicaÃ§Ã£o foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

Se falhar, revisar `.env`, base URL e prÃ©-requisitos.

## 5. Gerar preview seguro do request

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

Criterio para seguir:

- metodo `POST`;
- URL GraphQL oficial correta;
- header `Authorization` mascarado;
- `body.operationName=ShopeeOfferList`;
- `body.variables.limit=1`;
- nenhuma chamada HTTP executada;
- nenhuma publicacao executada;
- nenhum JSON salvo automaticamente.

## 6. Rodar status seguro do ambiente

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.safe_status --marketplace shopee
```

CritÃ©rio para seguir:

```text
INFO | Ambiente pronto para chamada real controlada
INFO | PublicaÃ§Ã£o real continua fora do escopo deste status.
```

Se o status retornar ambiente bloqueado, nÃ£o execute a chamada real.

## 7. Executar chamada real controlada

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --execute-real-http-once
```

CritÃ©rio de sucesso:

```text
INFO | Chamada HTTP real controlada concluÃ­da para marketplace=shopee
INFO | Ofertas normalizadas recebidas: 1
INFO | Nenhuma publicaÃ§Ã£o foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

CritÃ©rio de parada:

- erro HTTP;
- erro de transporte;
- erro de payload;
- saÃ­da com valor sensÃ­vel;
- quantidade inesperada;
- qualquer indÃ­cio de publicaÃ§Ã£o real.

## 8. Se houver payload bruto local

Se for necessÃ¡rio salvar o payload bruto para anÃ¡lise, usar apenas pasta ignorada pelo Git, como `tmp/`.

Depois, gerar fixture anonimizada:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.anonymize_payload --input tmp\raw-shopee-response.json --output tests\fixtures\shopee-real-anonymized.json
```

Antes de commitar a fixture:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_anonymized_fixture_safety.py
```

## O que continua proibido

- PublicaÃ§Ã£o real.
- Envio para grupos.
- Commit de `.env`.
- Commit de payload bruto.
- Commit de print sensÃ­vel.
- Aumentar `--limit` antes de validar a primeira resposta.
- Rodar chamadas repetidas sem entender erro anterior.

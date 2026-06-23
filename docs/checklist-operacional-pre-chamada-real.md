# Checklist operacional pré-chamada real

## Objetivo

Consolidar a ordem final de execução antes de qualquer chamada real controlada.

Este checklist não libera publicação real e não substitui a revisão manual dos contratos oficiais dos marketplaces.

## Regra principal

Pare imediatamente se qualquer etapa falhar, divergir do esperado ou mostrar valor sensível no terminal.

## 1. Atualizar repositório e validar testes

```powershell
cd C:\Automacao_Grupos-de-Ofertas
git pull
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

Critério para seguir:

- `ruff` sem erros;
- `pytest` sem erros.

## 2. Conferir contratos oficiais

Antes de configurar chamada real, revisar:

```text
docs/revisao-apis-marketplaces.md
docs/status-endpoint-shopee.md
docs/confirmacao-endpoint-shopee.md
```

Critério para seguir:

- host/base URL confirmado;
- endpoint confirmado;
- método confirmado;
- parâmetros obrigatórios confirmados;
- formato de assinatura confirmado;
- formato de resposta esperado compreendido.

## 3. Configurar `.env` local

Editar somente o `.env` local. Não editar o `.env.example` com valores reais.

Configurar apenas no ambiente local:

```text
ENABLE_REAL_HTTP=true
ENABLE_REAL_PUBLISH=false
SHOPEE_BASE_URL=<base-url-oficial>
SHOPEE_SEARCH_PATH=<path-oficial-confirmado>
```

Ainda não definir confirmação explícita do path antes do preview.

Critério para seguir:

- `.env` não versionado;
- publicação real desligada;
- path oficial configurado;
- nenhum valor real copiado para arquivos versionados.

## 4. Rodar diagnóstico de HTTP real

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --diagnose-real-http
```

Critério para seguir:

```text
INFO | Diagnóstico de HTTP real aprovado para marketplace=shopee
INFO | Nenhuma chamada HTTP foi executada.
INFO | Nenhuma publicação foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

Se falhar, revisar `.env`, base URL e pré-requisitos.

## 5. Gerar preview seguro do request

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

Critério para seguir:

- método correto;
- URL base correta;
- path correto;
- `page_size=1`;
- parâmetros sensíveis mascarados;
- nenhuma chamada HTTP executada;
- nenhuma publicação executada;
- nenhum JSON salvo automaticamente.

## 6. Confirmar explicitamente o endpoint

Somente depois do preview correto, definir no `.env` local:

```text
SHOPEE_SEARCH_PATH_CONFIRMED=true
```

Critério para seguir:

- confirmação feita apenas localmente;
- preview já revisado;
- contrato oficial confirmado.

## 7. Rodar status seguro do ambiente

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.safe_status --marketplace shopee
```

Critério para seguir:

```text
INFO | Ambiente pronto para chamada real controlada
INFO | Publicação real continua fora do escopo deste status.
```

Se o status retornar ambiente bloqueado, não execute a chamada real.

## 8. Executar chamada real controlada

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --execute-real-http-once
```

Critério de sucesso:

```text
INFO | Chamada HTTP real controlada concluída para marketplace=shopee
INFO | Ofertas normalizadas recebidas: 1
INFO | Nenhuma publicação foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

Critério de parada:

- erro HTTP;
- erro de transporte;
- erro de payload;
- saída com valor sensível;
- quantidade inesperada;
- qualquer indício de publicação real.

## 9. Se houver payload bruto local

Se for necessário salvar o payload bruto para análise, usar apenas pasta ignorada pelo Git, como `tmp/`.

Depois, gerar fixture anonimizada:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.anonymize_payload --input tmp\raw-shopee-response.json --output tests\fixtures\shopee-real-anonymized.json
```

Antes de commitar a fixture:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_anonymized_fixture_safety.py
```

## O que continua proibido

- Publicação real.
- Envio para grupos.
- Commit de `.env`.
- Commit de payload bruto.
- Commit de print sensível.
- Aumentar `--limit` antes de validar a primeira resposta.
- Rodar chamadas repetidas sem entender erro anterior.

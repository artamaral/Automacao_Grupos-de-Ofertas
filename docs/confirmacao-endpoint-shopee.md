# ConfirmaÃ§Ã£o explÃ­cita do endpoint da Shopee

> Nota: este documento registra o fluxo REST legado. O fluxo principal atual da Shopee usa GraphQL via `SHOPEE_GRAPHQL_URL` e nao depende de `SHOPEE_SEARCH_PATH_CONFIRMED`.

## Objetivo

Registrar a trava adicional criada para impedir chamada real da Shopee sem confirmaÃ§Ã£o manual do endpoint.

Essa trava existe porque o caminho atual usado pelo cÃ³digo ainda Ã© provisÃ³rio e precisa ser comparado com o contrato oficial da conta Shopee usada.

## VariÃ¡vel de confirmaÃ§Ã£o

A chamada real controlada da Shopee exige confirmaÃ§Ã£o explÃ­cita no ambiente local:

```text
SHOPEE_SEARCH_PATH_CONFIRMED=true
```

O valor padrÃ£o seguro Ã©:

```text
SHOPEE_SEARCH_PATH_CONFIRMED=false
```

## Regra de uso

SÃ³ definir a confirmaÃ§Ã£o como verdadeira depois de:

1. conferir o endpoint no painel ou documentaÃ§Ã£o oficial da conta Shopee usada;
2. rodar o diagnÃ³stico de HTTP real;
3. gerar o preview seguro do request;
4. comparar host, path, mÃ©todo e parÃ¢metros;
5. confirmar que nenhum valor sensÃ­vel apareceu no terminal.

## Bloqueio esperado

Se a chamada real controlada for executada sem confirmaÃ§Ã£o explÃ­cita, o harness deve bloquear a operaÃ§Ã£o.

SaÃ­da esperada:

```text
ERRO | Endpoint da Shopee nÃ£o confirmado para chamada real
DETALHE | Defina SHOPEE_SEARCH_PATH_CONFIRMED=true somente apÃ³s conferir o path oficial.
AÃ‡ÃƒO | Rode --print-provider-request e compare com a documentaÃ§Ã£o oficial.
```

Exit code esperado: `3`.

## Ordem segura

A ordem segura antes da primeira chamada real fica:

1. `ruff check .`
2. `pytest`
3. confirmar endpoint oficial
4. rodar `--diagnose-real-http`
5. rodar `--print-provider-request`
6. revisar manualmente o preview
7. definir confirmaÃ§Ã£o explÃ­cita no `.env` local
8. rodar `--execute-real-http-once` com `--limit 1`

## O que continua proibido

- NÃ£o confirmar endpoint sem revisÃ£o manual.
- NÃ£o commitar `.env`.
- NÃ£o commitar prints sensÃ­veis.
- NÃ£o executar chamada real se o preview divergir do contrato oficial.
- NÃ£o aumentar volume antes de validar a primeira resposta normalizada.

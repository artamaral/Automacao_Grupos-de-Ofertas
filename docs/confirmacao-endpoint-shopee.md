# ConfirmaÃ§Ã£o explÃ­cita do endpoint da Shopee

> Nota: este documento registra o fluxo REST legado. O fluxo principal atual da Shopee usa GraphQL via `SHOPEE_GRAPHQL_URL` e nao depende de `SHOPEE_SEARCH_PATH_CONFIRMED`.

## Objetivo

Registrar a regra operacional de confirmacao manual do endpoint antes da
primeira chamada real da Shopee.

No fluxo GraphQL atual, essa confirmacao e uma revisao manual obrigatoria do
operador. Ela nao e uma trava automatica aplicada pelo harness.

## Confirmacao manual

## Regra de uso

So considerar a chamada pronta depois de:

1. conferir o endpoint GraphQL no painel ou documentacao oficial da conta Shopee usada;
2. rodar o diagnÃ³stico de HTTP real;
3. gerar o preview seguro do request;
4. comparar host, metodo, `operationName` e variaveis;
5. confirmar que nenhum valor sensÃ­vel apareceu no terminal.

## Estado atual do harness

O harness hoje valida:

- `ENABLE_REAL_HTTP=true`;
- `ENABLE_REAL_PUBLISH=false`;
- `SHOPEE_PARTNER_ID` preenchido e numerico;
- `SHOPEE_SECRET_KEY` preenchido;
- `SHOPEE_TRACKING_ID` preenchido;
- `SHOPEE_GRAPHQL_URL` HTTPS e nao placeholder.

O harness nao aplica mais bloqueio automatico por `SHOPEE_SEARCH_PATH_CONFIRMED`
no fluxo principal GraphQL.

## Ordem segura

A ordem segura antes da primeira chamada real fica:

1. `ruff check .`
2. `pytest`
3. confirmar endpoint oficial
4. rodar `--diagnose-real-http`
5. rodar `--print-provider-request`
6. revisar manualmente o preview
7. registrar a confirmacao manual fora do Git, no processo operacional da execucao
8. rodar `--execute-real-http-once` com `--limit 1`

## O que continua proibido

- Nao considerar o endpoint confirmado sem revisao manual.
- NÃ£o commitar `.env`.
- NÃ£o commitar prints sensÃ­veis.
- NÃ£o executar chamada real se o preview divergir do contrato oficial.
- NÃ£o aumentar volume antes de validar a primeira resposta normalizada.

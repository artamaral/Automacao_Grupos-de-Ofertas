# Trava de confirmaÃ§Ã£o do endpoint Shopee

> Nota: este documento registra o fluxo REST legado. O fluxo principal atual da Shopee usa GraphQL via `SHOPEE_GRAPHQL_URL` e nao depende de `SHOPEE_SEARCH_PATH_CONFIRMED`.

## Objetivo

Registrar o historico da trava REST antiga e o que vale hoje no fluxo GraphQL.

## Achado

O caminho REST antigo da Shopee foi mantido como registro historico:

```text
/api/v2/product/search_item
```

Esse trecho existe apenas como legado. O fluxo principal atual da Shopee usa
GraphQL via `SHOPEE_GRAPHQL_URL`.

## Regra operacional atual

A primeira chamada real controlada da Shopee continua exigindo confirmacao
manual do operador, mas isso acontece por checklist e revisao operacional.

O harness atual nao bloqueia `--execute-real-http-once` com base em
`SHOPEE_SEARCH_PATH_CONFIRMED` no fluxo principal GraphQL.

## O que permanece permitido

Mesmo sem confirmaÃ§Ã£o explÃ­cita, continuam permitidos:

- testes locais;
- execuÃ§Ã£o com mock;
- diagnÃ³stico de HTTP real;
- preview seguro do request.

Esses modos nÃ£o publicam conteÃºdo. O diagnÃ³stico e o preview tambÃ©m nÃ£o executam chamada externa.

## O que permanece proibido

Sem confirmaÃ§Ã£o explÃ­cita do endpoint:

- nÃ£o executar chamada real controlada;
- nÃ£o aumentar limite;
- nÃ£o salvar payload real;
- nÃ£o publicar;
- nÃ£o transformar resposta real em fixture sem anonimizaÃ§Ã£o.

## CritÃ©rio para liberar

A liberaÃ§Ã£o exige:

1. confirmar o endpoint GraphQL oficial no painel/documentacao da conta Shopee usada;
2. revisar o contrato atual em `docs/checklist-operacional-pre-chamada-real.md`;
3. rodar diagnÃ³stico;
4. gerar preview seguro;
5. revisar manualmente o preview;
6. executar chamada real controlada com `--limit 1`.

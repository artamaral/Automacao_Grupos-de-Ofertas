# Trava de confirmaÃ§Ã£o do endpoint Shopee

> Nota: este documento registra o fluxo REST legado. O fluxo principal atual da Shopee usa GraphQL via `SHOPEE_GRAPHQL_URL` e nao depende de `SHOPEE_SEARCH_PATH_CONFIRMED`.

## Objetivo

Registrar a regra de seguranÃ§a criada para impedir chamada real da Shopee sem confirmaÃ§Ã£o explÃ­cita do endpoint.

## Achado

O caminho atual da Shopee foi mantido como padrÃ£o provisÃ³rio:

```text
/api/v2/product/search_item
```

Como esse caminho ainda depende de confirmaÃ§Ã£o manual contra a documentaÃ§Ã£o/painel oficial da conta usada, a execuÃ§Ã£o real controlada nÃ£o deve prosseguir apenas porque a guarda de HTTP real passou.

## Regra operacional

A primeira chamada real controlada da Shopee exige confirmaÃ§Ã£o explÃ­cita no ambiente local.

A confirmaÃ§Ã£o deve ser feita fora do Git com:

```text
SHOPEE_SEARCH_PATH_CONFIRMED=true
```

Sem essa confirmaÃ§Ã£o, o modo abaixo deve ser bloqueado:

```text
--execute-real-http-once
```

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

1. confirmar o path oficial no painel/documentaÃ§Ã£o da conta Shopee usada;
2. configurar `SHOPEE_SEARCH_PATH_CONFIRMED=true` apenas no `.env` local;
3. rodar diagnÃ³stico;
4. gerar preview seguro;
5. revisar manualmente o preview;
6. executar chamada real controlada com `--limit 1`.

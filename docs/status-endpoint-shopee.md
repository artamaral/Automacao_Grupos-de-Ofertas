# Status do endpoint da Shopee

## Objetivo

Registrar o estado atual do endpoint usado para a primeira chamada controlada da Shopee.

Este documento existe para impedir que uma chamada real seja feita sem revisão manual do endpoint contra a documentação oficial da conta usada no projeto.

## Estado atual no código

O fluxo principal atual da Shopee usa GraphQL.

O provider monta um request:

```text
POST https://open-api.affiliate.shopee.com.br/graphql
```

Com:

```text
operationName=ShopOfferList
query=shopOfferV2
```

A URL pode ser sobrescrita localmente por `SHOPEE_GRAPHQL_URL`, sem versionar
segredos ou credenciais.

O caminho REST `/api/v2/product/search_item` permanece documentado apenas como
legado/provisorio e nao e o fluxo principal atual.

## Status de verificação

Status atual: **GraphQL implementado e pendente de validacao com chamada real controlada**.

Antes de executar qualquer chamada real, conferir no ambiente oficial da Shopee:

- host/base URL correta para a conta e região;
- endpoint GraphQL correto;
- metodo `POST`;
- headers obrigatorios;
- formato correto da assinatura GraphQL;
- query `shopOfferV2`;
- campos obrigatórios de paginação/limite;
- formato esperado da resposta.

## Regra de segurança

Se o endpoint oficial ou o contrato GraphQL forem diferentes do codigo atual, nao executar a chamada real.

A ordem correta nesse caso é:

1. ajustar o builder GraphQL;
2. ajustar os testes de assinatura/request;
3. ajustar o preview seguro;
4. rodar `ruff` e `pytest`;
5. gerar novo preview;
6. somente então avaliar a chamada real controlada.

## Como revisar localmente

Depois de configurar o ambiente local, gerar o preview seguro:

```text
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

Conferir principalmente:

- `method`;
- `url`;
- `body.operationName`;
- `body.variables.limit`;
- header `Authorization` mascarado;
- ausência de valores sensíveis no terminal.

## O que não fazer

Não fazer:

- chamada real se o endpoint GraphQL ainda nao foi confirmado;
- tentativa repetida em caso de erro HTTP;
- commit de payload bruto;
- commit de print contendo valores sensíveis;
- aumento de limite antes de validar a primeira resposta.

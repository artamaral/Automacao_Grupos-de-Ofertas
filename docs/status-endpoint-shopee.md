# Status do endpoint da Shopee

## Objetivo

Registrar o estado atual do endpoint usado para a primeira chamada controlada da Shopee.

Este documento existe para impedir que uma chamada real seja feita sem revisão manual do endpoint contra a documentação oficial da conta usada no projeto.

## Estado atual no código

O builder atual monta o request da Shopee com:

```text
/api/v2/product/search_item
```

Esse caminho é usado para:

- montar a URL final do request;
- compor a base de assinatura;
- gerar o preview seguro no harness;
- executar a coleta real controlada quando a guarda permitir.

## Status de verificação

Status atual: **provisório e pendente de confirmação manual**.

Antes de executar qualquer chamada real, conferir no ambiente oficial da Shopee:

- host/base URL correta para a conta e região;
- caminho exato do endpoint de busca/listagem de produtos;
- método HTTP esperado;
- parâmetros obrigatórios;
- formato correto da assinatura;
- campos obrigatórios de paginação/limite;
- formato esperado da resposta.

## Regra de segurança

Se o endpoint oficial for diferente do caminho atual, não executar a chamada real.

A ordem correta nesse caso é:

1. ajustar o builder;
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
- caminho depois do host;
- `page_size`;
- parâmetros mascarados;
- ausência de valores sensíveis no terminal.

## O que não fazer

Não fazer:

- chamada real se o endpoint ainda não foi confirmado;
- tentativa repetida em caso de erro HTTP;
- commit de payload bruto;
- commit de print contendo valores sensíveis;
- aumento de limite antes de validar a primeira resposta.

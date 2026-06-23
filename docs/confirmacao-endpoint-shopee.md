# Confirmação explícita do endpoint da Shopee

## Objetivo

Registrar a trava adicional criada para impedir chamada real da Shopee sem confirmação manual do endpoint.

Essa trava existe porque o caminho atual usado pelo código ainda é provisório e precisa ser comparado com o contrato oficial da conta Shopee usada.

## Variável de confirmação

A chamada real controlada da Shopee exige confirmação explícita no ambiente local:

```text
SHOPEE_SEARCH_PATH_CONFIRMED=true
```

O valor padrão seguro é:

```text
SHOPEE_SEARCH_PATH_CONFIRMED=false
```

## Regra de uso

Só definir a confirmação como verdadeira depois de:

1. conferir o endpoint no painel ou documentação oficial da conta Shopee usada;
2. rodar o diagnóstico de HTTP real;
3. gerar o preview seguro do request;
4. comparar host, path, método e parâmetros;
5. confirmar que nenhum valor sensível apareceu no terminal.

## Bloqueio esperado

Se a chamada real controlada for executada sem confirmação explícita, o harness deve bloquear a operação.

Saída esperada:

```text
ERRO | Endpoint da Shopee não confirmado para chamada real
DETALHE | Defina SHOPEE_SEARCH_PATH_CONFIRMED=true somente após conferir o path oficial.
AÇÃO | Rode --print-provider-request e compare com a documentação oficial.
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
7. definir confirmação explícita no `.env` local
8. rodar `--execute-real-http-once` com `--limit 1`

## O que continua proibido

- Não confirmar endpoint sem revisão manual.
- Não commitar `.env`.
- Não commitar prints sensíveis.
- Não executar chamada real se o preview divergir do contrato oficial.
- Não aumentar volume antes de validar a primeira resposta normalizada.

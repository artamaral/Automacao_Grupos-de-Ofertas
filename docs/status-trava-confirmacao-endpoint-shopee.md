# Trava de confirmação do endpoint Shopee

## Objetivo

Registrar a regra de segurança criada para impedir chamada real da Shopee quando o endpoint ainda estiver no caminho provisório sem confirmação explícita.

## Achado

O caminho atual da Shopee foi mantido como padrão provisório:

```text
/api/v2/product/search_item
```

Como esse caminho ainda depende de confirmação manual contra a documentação/painel oficial da conta usada, a execução real controlada não deve prosseguir apenas porque a guarda de HTTP real passou.

## Regra operacional

Se `SHOPEE_SEARCH_PATH` estiver no valor provisório, a primeira chamada real controlada deve exigir confirmação explícita no ambiente local.

A confirmação deve ser feita fora do Git com:

```text
SHOPEE_SEARCH_PATH_CONFIRMED=true
```

Sem essa confirmação, o modo abaixo deve ser bloqueado:

```text
--execute-real-http-once
```

## O que permanece permitido

Mesmo sem confirmação explícita, continuam permitidos:

- testes locais;
- execução com mock;
- diagnóstico de HTTP real;
- preview seguro do request.

Esses modos não executam chamada externa ou não publicam conteúdo.

## O que permanece proibido

Sem confirmação explícita do endpoint:

- não executar chamada real controlada;
- não aumentar limite;
- não salvar payload real;
- não publicar;
- não transformar resposta real em fixture sem anonimização.

## Critério para liberar

A liberação exige:

1. confirmar o path oficial no painel/documentação da conta Shopee usada;
2. configurar `SHOPEE_SEARCH_PATH_CONFIRMED=true` apenas no `.env` local;
3. rodar diagnóstico;
4. gerar preview seguro;
5. revisar manualmente o preview;
6. executar chamada real controlada com `--limit 1`.

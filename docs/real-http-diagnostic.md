# Diagnóstico e execução HTTP real controlada

## Objetivo

Este documento descreve dois modos seguros para preparar uma chamada HTTP real:

1. diagnóstico de pré-requisitos, sem chamada externa;
2. execução HTTP real controlada, sem publicação e sem gravação automática.

Esses modos existem para reduzir risco antes da primeira chamada real de verdade.

## Diagnóstico sem chamada externa

O modo de diagnóstico valida se os pré-requisitos de HTTP real estão seguros sem executar chamada externa.

Ele serve para preparar a primeira chamada real controlada, mas não faz a chamada em si.

### Comando

Exemplo para Shopee:

```text
python -m ofertas_bot.harness --marketplace shopee --niche maquiagem --diagnose-real-http
```

Exemplo para Amazon:

```text
python -m ofertas_bot.harness --marketplace amazon --niche maquiagem --diagnose-real-http
```

### O que esse modo faz

O diagnóstico:

- valida a guarda de HTTP real;
- verifica se a flag de HTTP real está habilitada;
- verifica se a base URL é HTTPS;
- verifica se a base URL não é placeholder;
- verifica se os campos obrigatórios do provider estão presentes.

### O que esse modo não faz

O diagnóstico não:

- executa chamada HTTP;
- coleta ofertas;
- publica mensagens;
- salva JSON automaticamente;
- imprime valores sensíveis.

### Saída aprovada

Quando os pré-requisitos estão aprovados, a saída esperada é:

```text
INFO | Diagnóstico de HTTP real aprovado para marketplace=shopee
INFO | Nenhuma chamada HTTP foi executada.
INFO | Nenhuma publicação foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

Exit code esperado: `0`.

## Execução HTTP real controlada

O modo de execução controlada faz uma coleta HTTP real quando os pré-requisitos passam pela guarda.

Ele para logo após receber e normalizar as ofertas.

### Comando

Exemplo para Shopee:

```text
python -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --execute-real-http-once
```

Exemplo para Amazon:

```text
python -m ofertas_bot.harness --marketplace amazon --niche maquiagem --limit 1 --execute-real-http-once
```

### O que esse modo faz

A execução controlada:

- valida a guarda de HTTP real;
- cria o transport real somente se a guarda passar;
- executa uma coleta real;
- normaliza a resposta em ofertas;
- imprime apenas um resumo seguro.

### O que esse modo não faz

A execução controlada não:

- cria copy das ofertas;
- publica mensagens;
- salva JSON automaticamente;
- imprime valores sensíveis;
- envia qualquer conteúdo para grupos.

### Saída aprovada

Quando a chamada controlada termina com sucesso, a saída esperada é:

```text
INFO | Chamada HTTP real controlada concluída para marketplace=shopee
INFO | Ofertas normalizadas recebidas: 1
INFO | Nenhuma publicação foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

Exit code esperado: `0`.

## Saída bloqueada

Quando os pré-requisitos não estão seguros, a saída esperada é:

```text
ERRO | HTTP real bloqueado por configuração insegura
DETALHE | Real HTTP for <provider> is blocked: <motivo>
AÇÃO | Revise o checklist de produção antes de habilitar chamadas reais.
```

Exit code esperado: `3`.

## Marketplace mock

O diagnóstico não se aplica ao marketplace mock.

Saída esperada:

```text
WARN | Diagnóstico de HTTP real não se aplica ao marketplace mock.
AÇÃO | Use --marketplace shopee ou --marketplace amazon.
```

A execução controlada também não se aplica ao marketplace mock.

Saída esperada:

```text
ERRO | Chamada HTTP real não se aplica ao marketplace mock
AÇÃO | Use --marketplace shopee ou --marketplace amazon.
```

## Modos mutuamente exclusivos

Não use os dois modos juntos:

```text
--diagnose-real-http
--execute-real-http-once
```

Saída esperada:

```text
ERRO | Modo de HTTP real inválido
DETALHE | Use apenas um modo: --diagnose-real-http ou --execute-real-http-once.
AÇÃO | Rode primeiro o diagnóstico e depois a execução controlada.
```

Exit code esperado: `3`.

## Uso recomendado

Use esses modos antes de qualquer tentativa de chamada real em fluxo completo.

A ordem recomendada é:

1. configurar ambiente local fora do Git;
2. manter publicação real desligada;
3. habilitar HTTP real apenas em ambiente controlado;
4. rodar o diagnóstico;
5. revisar a saída;
6. rodar a execução controlada com `--limit 1`;
7. revisar a resposta normalizada;
8. transformar resposta real em fixture anonimizada antes de evoluir o fluxo.

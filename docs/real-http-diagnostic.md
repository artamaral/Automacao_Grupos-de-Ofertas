# Diagnóstico de HTTP real

## Objetivo

O modo de diagnóstico valida se os pré-requisitos de HTTP real estão seguros sem executar chamada externa.

Ele serve para preparar a primeira chamada real controlada, mas não faz a chamada em si.

## Comando

Exemplo para Shopee:

```text
python -m ofertas_bot.harness --marketplace shopee --niche maquiagem --diagnose-real-http
```

Exemplo para Amazon:

```text
python -m ofertas_bot.harness --marketplace amazon --niche maquiagem --diagnose-real-http
```

## O que esse modo faz

O diagnóstico:

- valida a guarda de HTTP real;
- verifica se a flag de HTTP real está habilitada;
- verifica se a base URL é HTTPS;
- verifica se a base URL não é placeholder;
- verifica se os campos obrigatórios do provider estão presentes.

## O que esse modo não faz

O diagnóstico não:

- executa chamada HTTP;
- coleta ofertas;
- publica mensagens;
- salva JSON automaticamente;
- imprime valores sensíveis.

## Saída aprovada

Quando os pré-requisitos estão aprovados, a saída esperada é:

```text
INFO | Diagnóstico de HTTP real aprovado para marketplace=shopee
INFO | Nenhuma chamada HTTP foi executada.
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

Exit code esperado: `0`.

## Uso recomendado

Use esse diagnóstico antes de qualquer tentativa de chamada real.

A ordem recomendada é:

1. configurar ambiente local fora do Git;
2. manter publicação real desligada;
3. habilitar HTTP real apenas em ambiente controlado;
4. rodar o diagnóstico;
5. revisar a saída;
6. só depois preparar uma chamada real sem publicação.

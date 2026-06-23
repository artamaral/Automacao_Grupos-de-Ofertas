# Status da guarda de HTTP real

## Objetivo

A guarda de HTTP real existe para impedir que chamadas externas sejam ativadas sem pré-requisitos mínimos de segurança.

Ela não conecta HTTP real por conta própria. Ela apenas valida se uma futura execução real está autorizada e configurada de forma segura.

## Concluído

A etapa atual implementou:

- módulo `src/ofertas_bot/providers/real_http_guard.py`;
- exceção `RealHttpValidationError`;
- estrutura `RealHttpPrerequisites`;
- função `validate_real_http_prerequisites()`;
- validação de flag explícita de HTTP real;
- validação de base URL HTTPS;
- bloqueio de base URL placeholder;
- validação de configurações obrigatórias por provider;
- integração passiva nos providers Shopee e Amazon;
- tratamento amigável no harness;
- testes unitários da guarda;
- testes da integração nos providers;
- teste do erro amigável no harness.

## Comportamento atual

A guarda só é acionada quando `enable_real_http=True`.

Com `enable_real_http=False`, o comportamento padrão continua seguro e sem chamada real.

Se a guarda bloquear a execução, o harness retorna:

```text
ERRO | HTTP real bloqueado por configuração insegura
DETALHE | Real HTTP for <provider> is blocked: <motivo>
AÇÃO | Revise o checklist de produção antes de habilitar chamadas reais.
```

Exit code esperado: `3`.

## O que a guarda bloqueia

A guarda bloqueia quando:

- a flag de HTTP real não está explicitamente habilitada;
- a base URL não usa HTTPS;
- a base URL ainda é placeholder;
- alguma configuração obrigatória do provider está ausente ou vazia.

## Integração atual

### Shopee

A guarda valida:

- flag de HTTP real;
- base URL da Shopee;
- identificador de parceiro;
- identificador de rastreamento;
- credencial de API.

### Amazon

A guarda valida:

- flag de HTTP real;
- base URL da Amazon;
- chave de acesso;
- credencial de API;
- tag de parceiro.

## O que ainda falta

Antes de ativar HTTP real, ainda falta:

1. validar base URLs reais fora do Git;
2. validar assinatura real da Shopee;
3. implementar ou validar assinatura real da Amazon;
4. conectar transport real somente atrás dessa guarda;
5. validar timeout;
6. validar retry e rate limit reais;
7. validar payload real anonimizado;
8. manter `enable_real_http=False` até aprovação manual.

## Relação com publicação real

A guarda de HTTP real não habilita publicação real.

Publicação real continua dependendo de uma trava separada e deve permanecer bloqueada até revisão manual completa.

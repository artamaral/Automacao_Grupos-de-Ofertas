# Resumo operacional atual

## Objetivo

Este documento resume o estado prático do projeto: o que já pode ser usado localmente, o que ainda é fake/controlado e o que falta antes de ativar HTTP real ou publicação real.

## O que já pode usar hoje

### Harness em dry-run

O harness pode ser executado localmente com marketplace mock:

```text
python -m ofertas_bot.harness --marketplace mock --niche maquiagem --limit 2
```

Esse fluxo executa:

1. coleta fake;
2. score;
3. criação de texto da oferta;
4. validação de compliance;
5. publicação simulada.

Nenhum envio real é feito.

### Salvar JSON local opcional

É possível salvar ofertas normalizadas em JSON apenas quando solicitado:

```text
python -m ofertas_bot.harness --marketplace mock --niche maquiagem --limit 2 --save-json ./.data/ofertas.json
```

O JSON serve para inspeção e debug local. Ele não deve conter credenciais, tokens, cookies, sessões, QR codes, headers de autenticação ou payload bruto sensível.

### Guarda de HTTP real

A guarda de HTTP real já existe e está integrada aos providers da Shopee e Amazon.

Ela é acionada somente quando `enable_real_http=True` e bloqueia a execução se:

- a base URL ainda for placeholder;
- a base URL não for HTTPS;
- alguma configuração obrigatória estiver ausente;
- a flag de HTTP real não estiver explicitamente habilitada.

Quando bloqueia, o harness retorna erro amigável e não exibe traceback.

### Testes automatizados

O projeto já possui testes para:

- harness;
- mensagens amigáveis de erro;
- providers fake/injetáveis;
- mappers;
- validação de payload;
- guarda de HTTP real;
- retry opcional;
- paginação fake;
- persistência JSON local;
- transport fake;
- transport HTTP isolado.

## O que ainda é fake ou controlado

### Providers externos

Shopee e Amazon ainda não fazem chamada real por padrão.

O comportamento atual usa:

- builders de request;
- gateways isolados;
- transport injetável;
- fixtures fake/anonimizadas;
- validações de payload;
- guarda de HTTP real.

Sem transport real conectado, não existe chamada externa automática.

### Paginação

A paginação existente é fake/opcional e usada para validar desenho técnico.

Ela cobre:

- múltiplas páginas;
- parada por `has_next_page`;
- parada por página vazia;
- parada por `limit`;
- parada por `max_pages`.

Antes de produção, precisa ser validada contra o contrato real de cada marketplace.

### Retry

Retry existe como política opcional.

Ele cobre:

- tentativas máximas;
- backoff;
- códigos retryable explícitos;
- sleeper fake nos testes.

Antes de produção, precisa ser combinado com os limites reais de cada API.

### Publicação

A publicação continua simulada via dry-run.

Não existe envio real para grupos.

## O que falta antes de HTTP real

Antes de qualquer chamada real, concluir:

1. revisar checklist de produção;
2. validar base URL real fora do Git;
3. validar assinatura real da Shopee;
4. implementar ou validar assinatura real da Amazon;
5. obter payload real anonimizado;
6. transformar payload real em fixtures seguras;
7. validar mappers com essas fixtures;
8. validar paginação real;
9. definir timeout e retry respeitando rate limit real;
10. conectar transport real somente atrás da guarda;
11. manter `enable_real_http=False` até aprovação manual.

## O que falta antes de publicação real

Antes de qualquer envio real, concluir:

1. manter `enable_real_publish=False` até aprovação manual;
2. revisar destinos reais;
3. confirmar que os grupos são opt-in;
4. validar mensagens com disclosure de afiliado;
5. testar fluxo completo em dry-run;
6. revisar logs para garantir ausência de dados sensíveis;
7. criar trava explícita de confirmação humana.

## Arquivos úteis

- `docs/production-checklist.md`;
- `docs/provider-fake-flow.md`;
- `docs/fake-artifacts-inventory.md`;
- `docs/status-paginacao-fake.md`;
- `docs/status-persistencia-json.md`;
- `docs/local-json-storage.md`;
- `docs/cli-messages.md`.

## Próximo foco sugerido

O próximo foco técnico recomendado é documentar a guarda de HTTP real em um status próprio e depois preparar a conexão futura do transport real atrás dessa guarda.

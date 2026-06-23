# Status do transport HTTP real

## Objetivo

Registrar a conexão controlada do transport HTTP real aos providers.

Essa etapa não ativa chamadas reais por padrão. Ela apenas prepara os providers para criarem o transport real quando a execução estiver explicitamente autorizada.

## Concluído

A etapa atual implementou:

- conexão de `UrllibHttpTransport` no provider da Shopee;
- conexão de `UrllibHttpTransport` no provider da Amazon;
- criação do transport apenas quando `enable_real_http=True`;
- manutenção do padrão seguro com `enable_real_http=False`;
- testes garantindo que o transport fica desligado por padrão;
- testes garantindo que o transport é criado quando a flag é ligada e a guarda passa.

## Comportamento atual

Com `enable_real_http=False`:

- o provider não cria transport real;
- nenhuma chamada externa é preparada automaticamente;
- o fluxo continua seguro para desenvolvimento local.

Com `enable_real_http=True`:

- a guarda de HTTP real valida os pré-requisitos;
- se a guarda passar, o provider cria `UrllibHttpTransport`;
- se a guarda bloquear, o harness mostra erro amigável e encerra com exit code `3`.

## Limites atuais

Essa etapa ainda não significa que o projeto está pronto para produção.

Ainda falta validar:

1. endpoints reais fora do Git;
2. assinatura e autenticação de cada marketplace;
3. timeout em ambiente real;
4. retry e rate limit com regras reais;
5. payload real anonimizado;
6. fixtures seguras baseadas em resposta real;
7. checklist de produção.

## Próximo passo técnico

O próximo passo recomendado é criar uma execução controlada de diagnóstico para HTTP real, sem publicação, sem persistência automática e com logs seguros.

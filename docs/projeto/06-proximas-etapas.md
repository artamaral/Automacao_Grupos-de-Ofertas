# Proximas etapas

## Prioridade imediata

Implementar a fundacao de dados no Supabase sem mover a descoberta local para
o runtime em nuvem.

## Sequencia recomendada

1. definir schema e migrations do Supabase
2. criar importacao idempotente do catalogo local curado
3. registrar versao, hash, profile e validacao de cada importacao
4. criar view de ranking e elegibilidade
5. migrar estado de selecao e cooldown
6. conectar geracao de mensagens ao Supabase
7. implementar launcher de mensagens no Cloud Run
8. remover o `n8n` do fluxo oficial

## Resultado esperado

Ao final desse bloco:

- a descoberta continua local e independente da operacao diaria em nuvem;
- o Supabase vira a fonte canonica do catalogo operacional publicado;
- ranking, estado e mensagens ficam auditaveis;
- o Cloud Run gera e dispara mensagens sem carregar a responsabilidade de
  descoberta.

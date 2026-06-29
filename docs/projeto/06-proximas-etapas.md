# Proximas etapas

## Prioridade imediata

Implementar a fundacao de dados no Supabase sem mover a descoberta local para
o runtime em nuvem.

## Estado atual

- [x] definir schema e migrations do Supabase;
- [x] criar view de ranking e elegibilidade;
- [x] criar estado persistente para selecao, cooldown e refresh;
- [ ] criar importacao idempotente do catalogo local curado;
- [ ] importar e validar os tres profiles reais;
- [ ] conectar geracao de mensagens ao Supabase;
- [ ] implementar launcher de mensagens no Cloud Run.

## Sequencia recomendada

1. criar importacao idempotente do catalogo local curado
2. registrar versao, hash, profile e validacao de cada importacao
3. importar e validar os catalogos dos tres profiles
4. conectar geracao de mensagens ao Supabase
5. implementar launcher de mensagens no Cloud Run
6. remover o `n8n` do fluxo oficial

## Resultado esperado

Ao final desse bloco:

- a descoberta continua local e independente da operacao diaria em nuvem;
- o Supabase vira a fonte canonica do catalogo operacional publicado;
- ranking, estado e mensagens ficam auditaveis;
- o Cloud Run gera e dispara mensagens sem carregar a responsabilidade de
  descoberta.

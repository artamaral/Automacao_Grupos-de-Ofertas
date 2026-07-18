# Proximas etapas

## Prioridade imediata

Fazer a primeira rodada MVP com n8n lendo o catalogo ativo do Supabase e
enviando apenas para destinos allowlisted.

## Estado atual

- [x] schema de catalogo e ranking criado no Supabase;
- [x] catalogos reais importados e ativados;
- [x] view `offers.v_offer_ranking_current` disponivel;
- [x] ledger `offers.publication_events` disponivel;
- [ ] query MVP do n8n validada contra 1 profile;
- [ ] template simples de mensagem configurado no n8n;
- [ ] allowlist de destino configurada no n8n;
- [ ] dry-run do workflow n8n validado;
- [ ] envio controlado para 1 destino allowlisted validado;
- [ ] registro idempotente em `publication_events` validado.

## Sequencia recomendada

1. Configurar credencial segura do Supabase no n8n.
2. Criar query do ranking com `is_eligible = true`, `profile`, `marketplace` e
   `limit`.
3. Montar mensagem por template simples dentro do n8n.
4. Bloquear envio quando o destino nao estiver na allowlist.
5. Executar dry-run com 1 profile e 1 destino de teste.
6. Enviar em modo controlado para o destino allowlisted.
7. Registrar tentativa e resultado em `offers.publication_events`.
8. Reexecutar o mesmo registro para validar idempotencia.

## Depois do MVP

- Automatizar a coleta para atualizar catalogos, reaproveitando os codigos de
  descoberta existentes.
- Revisar nichos, subnichos e falsos positivos semanticos, reaproveitando a
  base semantica atual e simplificando o fluxo quando essa frente for puxada.
- Avaliar se Cloud Run deve assumir parte da logica do n8n.
- Criar aprovacao humana mais completa, se a allowlist nao for suficiente.
- Melhorar metricas de performance por grupo e oferta.

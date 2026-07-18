# Analise operacional do projeto

> **Status: referencia do MVP.**
>
> A decisao de execucao vigente esta em
> [`docs/decisao-mvp-supabase-n8n.md`](decisao-mvp-supabase-n8n.md).

## Leitura atual

O projeto deve parar de sofisticar a arquitetura antes de provar a operacao
minima.

O caminho de MVP e:

```text
Catalogo ativo no Supabase
  -> n8n consulta ranking
  -> n8n monta mensagem
  -> n8n envia para allowlist
  -> Supabase registra historico
```

## O que ja existe

- Catalogos reais importados e ativados no Supabase.
- View `offers.v_offer_ranking_current` com ranking e elegibilidade.
- Tabela `offers.publication_events` para historico auditavel.
- Codigos de descoberta e classificacao semantica que ja rodam e podem ser
  reaproveitados em fase futura.
- Documentos e artefatos antigos de n8n, Cloud Run, CLI local e providers fake
  que podem servir como referencia.

## Gargalo atual

A documentacao anterior misturava arquitetura final, ferramentas de apoio,
checklists de chamada real e operacao diaria. Isso criou densidade antes de o
MVP estar em uso.

Para a fase atual, uma mudanca so deve entrar se ajudar diretamente:

- consultar ofertas elegiveis no Supabase;
- montar mensagens simples no n8n;
- bloquear destinos fora da allowlist;
- registrar envio ou bloqueio no Supabase;
- reduzir ambiguidade operacional.

## Fora da execucao minima

- Cloud Run como executor obrigatorio.
- Runner HTTP.
- Coleta automatica de catalogo.
- Revisao completa de nichos/subnichos.
- Regras finas de roteamento.
- Integracao real Shopee/Amazon durante a rodada diaria.

Esses pontos continuam validos como evolucao, mas nao bloqueiam o MVP. Quando
coleta e semantica voltarem para a pauta, a diretriz e reaproveitar os codigos
existentes que ja funcionam e simplificar sua operacao, em vez de recomecar a
implementacao do zero.

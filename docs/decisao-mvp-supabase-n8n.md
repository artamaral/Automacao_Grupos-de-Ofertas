# Decisao de arquitetura MVP Supabase e n8n

Este documento e a decisao canonica do MVP operacional.

Ele substitui, para a fase atual, a leitura anterior baseada em Supabase +
Cloud Run. Cloud Run permanece como evolucao futura ou ponte tecnica opcional,
mas nao e requisito para colocar o MVP em operacao.

## Decisao registrada

O fluxo oficial do MVP passa a ser:

```text
Catalogo ativo no Supabase
  -> n8n consulta ranking
  -> n8n monta mensagem
  -> n8n envia para allowlist
  -> Supabase registra historico
```

## Por que esta decisao existe

O projeto ficou denso demais para a fase atual. O MVP precisa provar a operacao
minima antes de ampliar a arquitetura.

Neste momento, o valor esta em:

- usar o catalogo que ja foi publicado no Supabase;
- selecionar ofertas elegiveis sem reexecutar descoberta;
- montar mensagens simples;
- enviar apenas para destinos controlados;
- registrar historico auditavel.

## Responsabilidades

### Supabase

Supabase e a fonte de verdade do MVP para:

- catalogo ativo;
- ranking e elegibilidade;
- estado minimo de selecao;
- historico de tentativas e envios.

### n8n

n8n e o orquestrador do MVP para:

- iniciar a rodada;
- consultar `offers.v_offer_ranking_current`;
- aplicar limite por rodada;
- montar `message_text`;
- validar allowlist de destino;
- enviar pelo canal configurado;
- gravar resultado em `offers.publication_events`.

### Repositorio

O repositorio guarda:

- migrations;
- contratos de dados;
- documentacao;
- scripts locais de apoio;
- referencias de template e regras.

### Cloud Run

Cloud Run nao faz parte do caminho obrigatorio do MVP.

Ele pode voltar depois se houver necessidade de:

- reduzir logica dentro do n8n;
- centralizar selecao/copy em Python;
- expor endpoints estaveis para workflows;
- escalar processamento fora do n8n.

## Contrato da query MVP

O n8n deve consultar `offers.v_offer_ranking_current` com filtros explicitos:

```sql
select
  profile,
  marketplace,
  stable_key,
  item_id,
  product_name,
  offer_link,
  price,
  reference_price,
  rating,
  sales_count,
  primary_subniche,
  commercial_score,
  score_reasons,
  rank_profile,
  rank_subniche
from offers.v_offer_ranking_current
where is_eligible = true
  and profile = :profile
  and marketplace = :marketplace
order by
  rank_profile nulls last,
  commercial_score desc,
  sales_count desc,
  rating desc nulls last,
  item_id
limit :limit;
```

O workflow nao deve inventar filtros escondidos. Qualquer filtro novo precisa
ser explicito e documentado.

## Segurança do MVP

- Credenciais ficam no n8n/Supabase, nunca no Git.
- O envio real so pode acontecer para destinos em allowlist.
- O workflow deve bloquear destino ausente da allowlist.
- O texto deve conter disclosure de afiliado.
- O registro em `publication_events` deve ser idempotente.

## Melhorias fora do MVP

- Automatizar coleta e atualizacao do catalogo.
- Revisar nichos e subnichos.
- Reaproveitar os codigos existentes de descoberta e classificacao semantica,
  porque eles ja rodam; quando essa frente entrar, o trabalho deve ser
  simplificar o fluxo, reduzir acoplamento e melhorar qualidade operacional,
  nao reescrever do zero.
- Calibrar score com evidencia de disparos.
- Criar revisao humana item a item.
- Mover partes do fluxo para Cloud Run.
- Adicionar dashboards e metricas de performance.

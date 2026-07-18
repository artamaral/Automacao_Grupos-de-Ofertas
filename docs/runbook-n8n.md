# Runbook n8n MVP

Este runbook descreve apenas o fluxo MVP.

Fluxos antigos com runner HTTP, self-hosted/local, Cloud Run ou Google
Planilhas como fonte principal ficam como referencia historica. Eles nao devem
guiar a primeira operacao minima.

## Fluxo oficial

```text
Trigger
  -> Definir contexto
  -> Consultar Supabase
  -> Montar mensagens
  -> Validar allowlist
  -> Enviar ou simular envio
  -> Registrar resultado no Supabase
```

## Entradas minimas

O workflow deve receber ou definir:

- `profile`: exemplo `feminino`;
- `marketplace`: exemplo `shopee`;
- `limit`: quantidade maxima de ofertas da rodada;
- `target`: destino logico do envio;
- `dry_run`: `true` por padrao;
- `run_id`: identificador da rodada.

## Credenciais

Configurar no n8n, fora do Git:

- conexao segura com Supabase;
- credencial do canal de envio;
- allowlist de destinos permitidos;
- template ou texto-base da mensagem.

## Query MVP

O node do Supabase deve consultar:

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

Regra: nao adicionar filtros escondidos. Qualquer filtro novo precisa aparecer
no workflow e na documentacao.

## Template minimo

O n8n deve montar `message_text` com os campos da query.

Template minimo:

```text
{{product_name}}

Preco: R$ {{price}}
Avaliacao: {{rating}}

Link: {{offer_link}}

Aviso: este link pode gerar comissao de afiliado. Preco e disponibilidade
podem mudar.
```

## Allowlist

Antes de qualquer envio real, o workflow deve verificar:

- `target` existe na allowlist;
- canal do target esta ativo;
- `dry_run` esta coerente com a etapa da rodada.

Se o destino nao estiver na allowlist, o workflow deve bloquear o envio e
registrar o bloqueio como resultado da rodada.

## Registro em publication_events

Apos tentativa de envio, o n8n deve gravar em `offers.publication_events`:

- `profile`;
- `marketplace`;
- `stable_key`;
- `item_id`;
- `target`;
- `channel_adapter`;
- `delivery_status`;
- `manifest_item_number`;
- `artifact_generated_at`;
- `sent_at`;
- `offer_title`;
- `offer_url`;
- `offer_price`;
- `message_text`;
- `payload`.

Retries nao devem duplicar publicacao. A chave operacional documentada em
[`supabase-publication-events.md`](supabase-publication-events.md) deve ser
preservada.

## Validacao minima

1. Rodar a query para 1 profile e confirmar ofertas elegiveis.
2. Rodar o workflow em `dry_run=true` para 1 destino allowlisted.
3. Testar destino fora da allowlist e confirmar bloqueio.
4. Rodar envio controlado para 1 destino allowlisted.
5. Registrar o resultado em `publication_events`.
6. Repetir o mesmo registro e confirmar que nao duplica.

## Fora do MVP

- Cloud Run.
- Runner HTTP.
- Revisao humana item a item.
- Coleta automatica do catalogo.
- Revisao completa dos nichos.
- Roteamento complexo por multiplos grupos.

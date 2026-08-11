# Pipeline de refresh de candidatos

## Decisao operacional

O catalogo ativo e um indice de discovery. Ele preserva identidade, profile e
taxonomia, mas nao e fonte atual de preco, comissao, vendas ou rating.

```text
catalogo ativo
  -> fila progressiva
  -> TTL
  -> productOfferV2 por itemId
  -> snapshot historico
  -> candidatos fresh
  -> ScorerAgent
  -> SelectionGate
```

A primeira versao atende somente `profile=feminino`, roda manualmente e nao
altera `offers.catalog_items`.

## Fila progressiva

A fila usa apenas metadados de discovery e segue esta prioridade:

1. `MISSING` nunca tentado;
2. `MISSING` com tentativa anterior, da mais antiga para a mais recente;
3. `STALE`, do snapshot mais antigo para o mais recente;
4. `FRESH`, somente para completar o pre-batch.

Itens atualizados com sucesso tornam-se `FRESH` e deixam a frente da fila. Uma
falha gera uma linha em `offer_refresh_attempts`; com isso, itens nunca tentados
passam a frente na proxima rodada.

Dentro de cada prioridade, a selecao usa as quotas de
`config/selection_profiles.toml`, dedupe por `marketplace + item_id` e
diversidade de seller em passes sucessivos. Preco, comissao, desconto, vendas,
rating e score antigos nao participam da fila.

## TTL e estruturas

`offers.candidate_refresh_policies` e a fonte unica do TTL. O valor inicial de
`feminino/shopee` e 24 horas e a constraint nao permite valor menor.

- `offer_snapshots`: uma linha para cada verificacao externa bem-sucedida;
- `offer_refresh_attempts`: uma linha para cada chamada real, inclusive erro;
- `v_offer_latest_snapshot`: ultimo snapshot por item;
- `v_offer_refresh_status`: `MISSING`, `FRESH` ou `STALE` no catalogo ativo;
- `v_offer_scoring_current`: metadados do catalogo mais estado comercial fresh.

Cache hit nao gera tentativa nem snapshot. `checked_at` representa o momento da
chamada externa, nao a leitura do banco.

O `source_payload` contem somente `itemId/page/limit`, o node retornado e
`pageInfo`. Headers, assinatura e credenciais nao sao persistidos.

## Execucao manual

Dry-run, tambem usado quando nenhuma flag de escrita e informada:

```powershell
.\.venv\Scripts\python.exe scripts\shopee\run_candidate_refresh.py `
  --profile feminino `
  --discovery-limit 600 `
  --scoring-limit 200 `
  --dry-run
```

O dry-run consulta o banco, monta a fila e estima chamadas. Ele nao chama a
Shopee e nao grava tentativa ou snapshot.

Execucao real limitada:

```powershell
.\.venv\Scripts\python.exe scripts\shopee\run_candidate_refresh.py `
  --profile feminino `
  --discovery-limit 20 `
  --scoring-limit 20 `
  --max-api-calls 20 `
  --apply `
  --confirm-remote-write REFRESH_SHOPEE_CANDIDATES
```

Para validar um item especifico do catalogo ativo:

```powershell
.\.venv\Scripts\python.exe scripts\shopee\run_candidate_refresh.py `
  --profile feminino `
  --item-id 123456789 `
  --scoring-limit 1 `
  --max-api-calls 1 `
  --apply `
  --confirm-remote-write REFRESH_SHOPEE_CANDIDATES
```

Ao atingir `--max-api-calls`, a rodada fica `partial`, preserva o que ja foi
gravado e marca os demais itens como `deferred_api_limit` apenas no artefato.
Como nao houve chamada para esses itens, nao existe tentativa no banco.

## Artefatos

Cada rodada grava em `.data/candidate_refresh/<profile>/<run_id>/`:

- `discovery_candidates.csv`;
- `refresh_attempts.csv`;
- `scoring_candidates.csv`;
- `scored_candidates.csv`;
- `selected_offers.csv`;
- `run_report.json`.

Os arquivos sao auditoria local. A verdade historica permanece no Supabase.

## Erros e limitacoes

- erro HTTP preserva o ultimo snapshot e registra `technical_failure`;
- payload inconsistente registra `invalid_payload`;
- resposta sem node registra `no_node`, mas nao prova indisponibilidade;
- a API consultada nao entrega campo explicito de frete, disponibilidade ou
  elegibilidade de afiliado no contrato atual;
- frete fica desconhecido e nao recebe pontos no scorer;
- somente snapshot `FRESH`, com preco positivo, `offerLink` e rating dentro da
  elegibilidade atual entra no score;
- feeds 10k/100k, scheduler, n8n e publicacao permanecem fora deste fluxo.

## Payload real validado

O smoke test de 2026-08-11 confirmou estes campos no node de
`productOfferV2(itemId)`:

```text
appExistRate, appNewRate, commission, commissionRate, imageUrl, itemId,
offerLink, periodEndTime, periodStartTime, price, priceDiscountRate, priceMax,
priceMin, productCatIds, productLink, productName, ratingStar, sales,
sellerCommissionRate, shopeeCommissionRate, shopId, shopName, shopType,
webExistRate, webNewRate
```

O retorno nao incluiu `freeShipping`, disponibilidade ou status explicito de
elegibilidade. Uma resposta vazia continua inconclusiva e nao cria snapshot de
indisponibilidade.

## Migration e validacao

Inspecao read-only:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\apply_migrations.py
```

Aplicacao explicita:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\apply_migrations.py `
  --apply `
  --confirm-remote-write APPLY_SUPABASE_MIGRATIONS
```

Validacao com fixture revertida ao final:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\validate_catalog_schema.py
```

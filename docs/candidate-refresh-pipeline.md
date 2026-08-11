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

## Fila orientada ao ranking

A fila atualiza primeiro a fronteira que pode chegar a copy. Ela considera
somente itens elegiveis do catalogo ativo, separa por `primary_subniche` e
ordena cada banda por `rank_subniche`, `commercial_score desc` e `item_id`.
`MISSING` e `STALE` disputam pela posicao no ranking: um `STALE` melhor colocado
vem antes de um `MISSING` pior colocado.

Uma execucao padrao distribui ate 500 chamadas reais:

- 80%, ou 400, para a fronteira do ranking;
- 20%, ou 100, para `MISSING` nunca tentados fora da fronteira;
- se a descoberta nao preencher 100 vagas, a sobra volta para os proximos
  `MISSING/STALE` das bandas do ranking.

As quotas de `config/selection_profiles.toml` escalam de 20 para 500. No
profile `feminino`, cada banda de 10% recebe 40 vagas de ranking e 10 de
descoberta; cada banda de 5% recebe 20 e 5, respectivamente. Dedupe por
`marketplace + item_id` e diversidade de seller continuam obrigatorios.

Itens `FRESH` encontrados durante a varredura geram cache hit, nao ocupam vaga
de chamada e fazem a fila avancar ate o proximo `MISSING/STALE`. Falha ou
`no_node` gera tentativa auditavel sem remover o ultimo snapshot valido.

## TTL e estruturas

`offers.candidate_refresh_policies` e a fonte unica do TTL. O valor inicial de
`feminino/shopee` e 24 horas e a constraint nao permite valor menor.

- `offer_snapshots`: uma linha para cada verificacao externa bem-sucedida;
- `offer_refresh_attempts`: uma linha para cada chamada real, inclusive erro;
- `v_offer_latest_snapshot`: ultimo snapshot por item;
- `v_offer_refresh_status`: `MISSING`, `FRESH` ou `STALE` no catalogo ativo;
- `v_offer_scoring_current`: metadados do catalogo mais o ultimo estado
  comercial, com fallback por campo para o catalogo.

Cache hit nao gera tentativa nem snapshot. `checked_at` representa o momento da
chamada externa, nao a leitura do banco.

O `source_payload` contem somente `itemId/page/limit`, o node retornado e
`pageInfo`. Headers, assinatura e credenciais nao sao persistidos.

## Execucao manual

Dry-run, tambem usado quando nenhuma flag de escrita e informada:

```powershell
.\.venv\Scripts\python.exe scripts\shopee\run_candidate_refresh.py `
  --profile feminino `
  --discovery-limit 500 `
  --scoring-limit 200 `
  --dry-run
```

O dry-run consulta o banco, monta a fila e estima chamadas. Ele nao chama a
Shopee e nao grava tentativa ou snapshot.

## Execucao agendada na VPS

O refresh operacional roda fora do n8n, por `systemd timer`, na VPS Hostinger.
O n8n continua consultando `offers.v_offer_ranking_current`; o timer apenas
atualiza snapshots antes da primeira publicacao do dia.

- horario: 07:00 BRT, diario;
- app path: `/opt/automacao_grupo_compras/app`;
- n8n path: `/opt/automacao_grupo_compras/n8n`;
- service: `shopee-candidate-refresh.service`;
- timer: `shopee-candidate-refresh.timer`;
- wrapper: `scripts/ops/run_shopee_candidate_refresh.sh`;
- units versionados: `deploy/systemd/shopee-candidate-refresh.*`.

Como a VPS esta em UTC, o timer usa timezone explicito:

```ini
OnCalendar=*-*-* 07:00:00 America/Sao_Paulo
```

O wrapper usa `flock`, preserva os artefatos locais e executa:

```bash
/opt/automacao_grupo_compras/app/.venv/bin/python \
  /opt/automacao_grupo_compras/app/scripts/shopee/run_candidate_refresh.py \
  --profile feminino \
  --marketplace shopee \
  --discovery-limit 500 \
  --scoring-limit 200 \
  --max-api-calls 500 \
  --apply \
  --confirm-remote-write REFRESH_SHOPEE_CANDIDATES
```

Credenciais reais ficam somente no `.env` local da VPS, fora do Git. Antes de
habilitar o timer, validar SSH, `git pull`, Python 3.11+, `.venv`, `.env`,
`validate_catalog_schema.py`, dry-run de 500 e smoke real de 1 item.

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
- `ranking_changes.csv`;
- `run_report.json`.

Os arquivos sao auditoria local. A verdade historica permanece no Supabase.

## Erros e limitacoes

- erro HTTP preserva o ultimo snapshot e registra `technical_failure`;
- payload inconsistente registra `invalid_payload`;
- resposta sem node registra `no_node`, mas nao prova indisponibilidade;
- a API consultada nao entrega campo explicito de frete, disponibilidade ou
  elegibilidade de afiliado no contrato atual;
- frete fica desconhecido e nao recebe pontos no scorer;
- o ranking usa o ultimo snapshot mesmo quando `STALE`; sem snapshot ou sem
  valor em um campo, usa o dado correspondente do catalogo;
- `commercial_data_source`, `refresh_status`, `last_checked_at` e `age_hours`
  deixam explicita a idade e a origem do score;
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

## Rollout orientado ao ranking

Validacao real de 2026-08-11:

- dry-run: 400 candidatos de ranking, 100 de descoberta e 19 cache hits;
- smoke real: 5 chamadas, 5 snapshots e 5 mudancas de `catalog` para `snapshot`;
- lote real: 500 chamadas em 683 segundos, 490 snapshots e 10 respostas `no_node`;
- distribuicao realizada: 50 candidatos por banda de 10% e 25 por banda de 5%;
- entre os 490 itens atualizados, 62 scores subiram, 303 cairam e 125 ficaram iguais;
- 9 itens deixaram de ser elegiveis depois do refresh;
- os 490 IDs de snapshot foram confirmados no Supabase;
- depois do lote, o top 20 de `feminino` ficou integralmente em
  `commercial_data_source=snapshot` e `refresh_status=FRESH`.

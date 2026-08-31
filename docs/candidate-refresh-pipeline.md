# Pipeline de refresh de candidatos

## Decisao operacional

O catalogo persistente e um indice de discovery. Ele preserva identidade, profile e
taxonomia, mas nao e fonte atual de preco, comissao, vendas ou rating.

```text
catalogo persistente
  -> fila progressiva
  -> TTL
  -> productOfferV2 por itemId
  -> snapshot historico
  -> candidatos fresh
  -> ScorerAgent
  -> SelectionGate
```

A implementacao atende somente `profile=feminino`, roda diariamente pelo
service versionado e nao altera `offers.catalog_items`.

## Fila orientada ao ranking

A fila atualiza primeiro a fronteira que pode chegar a copy. Ela considera
somente itens elegiveis do catalogo persistente, separa por `primary_subniche` e
ordena cada banda por `rank_subniche`, `commercial_score desc` e `item_id`.
`MISSING` e `STALE` disputam pela posicao no ranking: um `STALE` melhor colocado
vem antes de um `MISSING` pior colocado.

Uma execucao padrao distribui ate 1000 chamadas reais:

- 80%, ou 800, para a fronteira do ranking;
- 20%, ou 200, para `MISSING` nunca tentados fora da fronteira;
- se a descoberta nao preencher 200 vagas, a sobra volta para os proximos
  `MISSING/STALE` das bandas do ranking.

As quotas de `config/selection_profiles.toml` escalam de 20 para 1000. No
profile `feminino`, cada banda de 10% recebe 80 vagas de ranking e 20 de
descoberta; cada banda de 5% recebe 40 e 10, respectivamente. Dedupe por
`marketplace + item_id` e diversidade de seller continuam obrigatorios.

Itens `FRESH` encontrados durante a varredura geram cache hit, nao ocupam vaga
de chamada e fazem a fila avancar ate o proximo `MISSING/STALE`. Falha ou
`no_node` gera tentativa auditavel sem remover o ultimo snapshot valido.
Quando a operacao confirmar manualmente que um `no_node` representa item
indisponivel, o item pode receber `refresh_status=UNAVAILABLE_CONFIRMED`; nessa
condicao ele sai da fila automatica diaria e so volta a ser consultado por
rechecagem explicita de `item_id`.

## TTL e estruturas

`offers.candidate_refresh_policies` e a fonte unica do TTL. O valor inicial de
`feminino/shopee` e 24 horas e a constraint nao permite valor menor.

- `offer_snapshots`: uma linha para cada verificacao externa bem-sucedida;
- `offer_refresh_attempts`: uma linha para cada chamada real, inclusive erro;
- `v_offer_latest_snapshot`: ultimo snapshot por item;
- `v_offer_refresh_status`: `MISSING`, `FRESH`, `STALE` ou `UNAVAILABLE_CONFIRMED`
  no catalogo persistente;
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
  --discovery-limit 1000 `
  --scoring-limit 1000 `
  --dry-run
```

O dry-run consulta o banco, monta a fila e estima chamadas. Ele nao chama a
Shopee e nao grava tentativa ou snapshot.

Para confirmar manualmente uma rodada ja inspecionada:

```powershell
.\.venv\Scripts\python.exe scripts\shopee\confirm_candidate_unavailable.py `
  --profile feminino `
  --refresh-attempts-file .data\candidate_refresh\feminino\<run_id>\refresh_attempts.csv `
  --apply `
  --confirm-remote-write CONFIRM_CANDIDATE_UNAVAILABLE
```

## Execucao agendada na VPS

O refresh operacional roda fora do n8n, por `systemd timer`, na VPS Hostinger.
Para `feminino`, o mesmo service gera a fila diaria depois de atualizar os
snapshots. O n8n nao consulta o ranking nem planeja bandas: consome apenas
`offers.v_daily_dispatch_ready` depois que a cadeia termina.

- horario: 06:30 BRT, diario;
- app path: `/opt/automacao_grupo_compras/app`;
- n8n path: `/opt/automacao_grupo_compras/n8n`;
- service: `shopee-candidate-refresh.service`;
- timer: `shopee-candidate-refresh.timer`;
- usuario do service: `ofertas-refresh`;
- wrapper: `scripts/ops/run_shopee_candidate_refresh.sh`;
- units versionados: `deploy/systemd/shopee-candidate-refresh.*`.

Como a VPS esta em UTC, o timer usa timezone explicito:

```ini
OnCalendar=*-*-* 06:30:00 America/Sao_Paulo
```

O wrapper usa um unico `flock` durante toda a cadeia, preserva os artefatos
locais, executa o refresh real e, por padrao, roda um pos-processo que confirma
automaticamente itens com `no_node` recorrente. Depois dessa pos-etapa, ou
diretamente depois do refresh quando ela esta desabilitada, o wrapper persiste
o plano de 140 slots por `product_cat_id`. Qualquer erro impede as etapas seguintes e deixa o
service com falha. O limite padrao de recorrencia e
`AUTO_CONFIRM_UNAVAILABLE_MIN_NO_NODE_ATTEMPTS=2`.

```bash
/opt/automacao_grupo_compras/app/.venv/bin/python \
  /opt/automacao_grupo_compras/app/scripts/shopee/run_candidate_refresh.py \
  --profile feminino \
  --marketplace shopee \
  --productcatid-matrix config/shopee_productcatid_quotas_feminino.csv \
  --discovery-limit 140 \
  --scoring-limit 140 \
  --max-api-calls 140 \
  --apply \
  --confirm-remote-write REFRESH_SHOPEE_CANDIDATES
```

Pos-etapa automatica do wrapper:

```bash
/opt/automacao_grupo_compras/app/.venv/bin/python \
  /opt/automacao_grupo_compras/app/scripts/shopee/auto_confirm_candidate_unavailable.py \
  --profile feminino \
  --marketplace shopee \
  --refresh-attempts-file .data/candidate_refresh/feminino/<run_id>/refresh_attempts.csv \
  --min-no-node-attempts 2 \
  --apply \
  --confirm-remote-write AUTO_CONFIRM_CANDIDATE_UNAVAILABLE
```

Etapa final obrigatoria do mesmo wrapper:

```bash
/opt/automacao_grupo_compras/app/.venv/bin/python \
  -m ofertas_bot.tools.plan_daily_dispatch \
  --profile feminino \
  --marketplace shopee \
  --productcatid-matrix config/shopee_productcatid_quotas_feminino.csv \
  --apply
```

Variaveis operacionais do wrapper:

- `AUTO_CONFIRM_UNAVAILABLE_ENABLED=true` ativa a pos-etapa automatica;
- `AUTO_CONFIRM_UNAVAILABLE_MIN_NO_NODE_ATTEMPTS=2` exige recorrencia antes da
  confirmacao automatica;
- `AUTO_CONFIRM_UNAVAILABLE_REASON` personaliza a justificativa gravada no
  ledger;
- `AUTO_CONFIRM_UNAVAILABLE_CONFIRMATION=AUTO_CONFIRM_CANDIDATE_UNAVAILABLE`
  protege a escrita remota da pos-etapa.

Desabilitar a confirmacao automatica nao desabilita o planejamento. Nao existe
timer separado para `plan_daily_dispatch`.

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

Para validar um item especifico do catalogo persistente:

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
- confirmacao manual de indisponibilidade grava `confirmed_unavailable` no
  ledger de tentativas e muda o status operacional para
  `UNAVAILABLE_CONFIRMED`;
- confirmacao automatica de indisponibilidade so ocorre depois de recorrencia
  configurada de `no_node` e registra `source=auto_confirmed_unavailable`;
- a API consultada nao entrega campo explicito de frete, disponibilidade ou
  elegibilidade de afiliado no contrato atual;
- frete fica desconhecido e nao recebe pontos no scorer;
- o ranking usa o ultimo snapshot mesmo quando `STALE`; sem snapshot ou sem
  valor em um campo, usa o dado correspondente do catalogo;
- `commercial_data_source`, `refresh_status`, `last_checked_at` e `age_hours`
  deixam explicita a idade e a origem do score;
- o planejador diario do `feminino` nao consome itens `STALE`: ele carrega
  apenas linhas `refresh_status='FRESH'` de `offers.v_offer_ranking_current`;
- se o refresh terminar sem candidatos `FRESH` suficientes para preencher os
  112 slots, o planejador falha e nao persiste plano parcial;
- um slot planejado que fique `STALE` depois disso continua auditavel em
  `offers.daily_dispatch_plan`, mas deixa de aparecer como pronto em
  `offers.v_daily_dispatch_ready`;
- feeds 10k/100k, discovery ampla, n8n e publicacao permanecem fora desta
  cadeia; somente o planejamento diario persistido foi acoplado ao refresh.

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
eligibilidade. Uma resposta vazia continua inconclusiva e nao cria snapshot de
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

## Relacao com a fila diaria

O refresh comercial continua sendo a fonte da freshness operacional do
`feminino`, mas o consumo nao depende apenas da ordem do cron. O contrato
vigente e:

```text
refresh/rechecagem
  -> ranking pode continuar exibindo itens stale para diagnostico e priorizacao
  -> planner diario persiste apenas candidatos FRESH
  -> v_daily_dispatch_ready revalida freshness antes do claim
  -> n8n so claima slots aprovados pela view
```

Essa separacao evita que um item stale entre no envio mesmo quando o plano foi
gravado antes de uma mudanca de freshness.

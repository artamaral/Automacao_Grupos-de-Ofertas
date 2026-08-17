# Spec — Refresh diário D0 para planejamento e dispatch

Status: **NÃO IMPLEMENTADA**

Esta especificação define a mudança de validade operacional do refresh para o fluxo diário de ofertas. Enquanto este documento permanecer em `docs/specs-nao-implementadas/`, ele deve ser tratado como proposta aprovada para implementação futura, não como comportamento já existente em produção.

## 1. Objetivo

Garantir que todo item utilizado no plano diário de dispatch tenha sido atualizado no marketplace no próprio dia operacional, considerando explicitamente o timezone `America/Sao_Paulo`.

A regra operacional deixa de depender do TTL móvel de 24 horas para decidir se um item pode participar do planejamento e do dispatch do dia.

A regra passa a ser:

```text
refresh em D0  -> OK
refresh em D-1 -> NOK
```

O horário intradiário do refresh não importa.

## 2. Problema atual

Hoje o fluxo usa `refresh_status = FRESH`, onde `FRESH` representa essencialmente uma janela móvel de 24 horas desde `last_checked_at`.

Isso permite o seguinte cenário:

```text
16/08 08:00
ultimo refresh

17/08 06:30
candidate refresh

idade do snapshot = 22h30
-> FRESH
-> cache_hit
-> API nao e chamada

17/08 06:51
plan_daily_dispatch

idade = 22h51
-> ainda FRESH
-> produto entra no plano

17/08 08:00
snapshot completa 24h
-> STALE

publicacoes posteriores
-> is_ready_for_dispatch = false
```

No plano analisado de `17/08/2026`:

```text
112 itens planejados
50 -> ultimo refresh em 17/08
62 -> ultimo refresh em 16/08
```

Os 62 itens de D-1 eram tecnicamente `FRESH` no momento da criação do plano, mas ficaram `STALE` durante o mesmo dia.

## 3. Nova regra operacional

Para participar da operação do dia `D`, o item deve possuir snapshot produzido em `D`.

Formalmente:

```text
local_date(last_checked_at) == operational_date
```

onde `local_date` deve ser calculada em `America/Sao_Paulo`.

Exemplos para `operational_date = 17/08`:

```text
refresh 17/08 00:01 -> OK
refresh 17/08 06:30 -> OK
refresh 16/08 23:59 -> NOK
refresh 16/08 08:00 -> NOK
```

Não deve haver comparação operacional baseada em `23h`, `23h30`, `23h59` ou `24h01`. Para a operação diária, somente a data importa.

## 4. Separação entre TTL técnico e validade operacional

O TTL atual de 24 horas não deve ser removido.

Ele continua existindo para observabilidade e outros usos por meio de `refresh_status`, incluindo estados como `FRESH`, `STALE`, `MISSING` e demais estados existentes.

Porém, `refresh_status = FRESH` deixa de ser suficiente para planejamento e dispatch.

A validade operacional passa a ser:

```text
refreshed_today = local_date(last_checked_at) == operational_date
```

Consequências:

```text
FRESH + D-1
-> tecnicamente fresh
-> operacionalmente invalido

FRESH + D0
-> tecnicamente fresh
-> operacionalmente valido
```

## 5. Regra do candidate refresh

### Comportamento atual

O `candidate_refresh.py` usa o estado técnico de freshness para decidir o cache:

```python
if candidate.refresh_status == "FRESH":
    cache_hit
else:
    refresh_api
```

### Novo comportamento

O job deve trabalhar com uma `operational_date` explícita.

Para cada candidato:

```python
if candidate.last_checked_at is not None \
   and local_date(candidate.last_checked_at) == operational_date:
    cache_hit
else:
    refresh_api
```

Resultado esperado:

```text
snapshot D0         -> CACHE HIT
snapshot D-1        -> REFRESH
snapshot D-2        -> REFRESH
snapshot mais velho -> REFRESH
MISSING             -> REFRESH
```

O fato de um snapshot de D-1 ainda estar dentro das últimas 24 horas não deve impedir a atualização.

## 6. Data operacional

Toda lógica deve utilizar explicitamente:

```text
America/Sao_Paulo
```

Não deve depender do timezone implícito da VPS, PostgreSQL, sessão SQL ou processo Python.

Para execução diária normal:

```text
operational_date = hoje em America/Sao_Paulo
```

Para planejamento:

```text
operational_date = planned_date
```

Exemplo SQL:

```sql
(last_checked_at AT TIME ZONE 'America/Sao_Paulo')::date
```

## 7. Fluxo esperado

```text
06:30
candidate refresh
        |
        v
seleciona discovery candidates
        |
        v
snapshot em D0?
   |             |
  SIM           NAO
   |             |
cache_hit     consulta Shopee
                 |
                 v
          salva snapshot D0
                 |
                 v
        recalcula score/ranking
                 |
                 v
somente candidatos com snapshot D0
podem seguir para scoring
                 |
                 v
          SelectionGate
                 |
                 v
      plan_daily_dispatch
                 |
                 v
somente candidatos com snapshot D0
                 |
                 v
             112 slots
                 |
                 v
       dispatch durante D0
```

## 8. Regra pós-refresh para scoring

Depois do loop de refresh, não é suficiente utilizar apenas `is_scoring_ready`.

Um item pode ter snapshot de D-1 ainda dentro do TTL técnico e sofrer uma tentativa D0 com falha. Nesse caso, ele não pode seguir para scoring apenas porque o snapshot antigo ainda é tecnicamente `FRESH`.

O universo pós-refresh precisa satisfazer:

```text
is_scoring_ready
AND snapshot_date == operational_date
```

Exemplo:

```text
snapshot de ontem
-> refresh hoje falhou
-> snapshot atual continua sendo D-1
-> nao entra no scoring
```

## 9. Regra do planner

O `plan_daily_dispatch` só pode receber candidatos que atendam:

```text
is_eligible = true
AND snapshot_date = planned_date
```

O filtro `refresh_status = 'FRESH'` não deve ser considerado suficiente.

A regra desejada é equivalente a:

```sql
where profile = ?
  and marketplace = ?
  and is_eligible
  and (
      last_checked_at at time zone 'America/Sao_Paulo'
  )::date = planned_date
```

## 10. Fallbacks do planner

As regras existentes de `fixed_daily`, `weekly_rotation`, `redistributed` e `top_score_fallback` devem permanecer inalteradas.

Todo fallback deve operar exclusivamente sobre o universo previamente validado:

```text
eligible
AND refreshed em D0
```

Nenhum fallback pode buscar ou aceitar itens de D-1.

## 11. Falha segura

Se não houver candidatos D0 suficientes para cumprir o plano, o sistema não deve completar os slots com itens antigos.

Exemplo:

```text
necessarios = 112
candidatos validos apos quotas = 108
```

Resultado esperado:

```text
planejamento falha
```

Resultado proibido:

```text
108 D0
+
4 D-1
```

O erro deve ser explícito.

## 12. Readiness do dispatch

A regra operacional de readiness passa a considerar o dia do snapshot:

```text
is_ready_for_dispatch =
    dispatch_status == planned
    AND is_eligible
    AND snapshot_date == planned_date
```

O TTL de 24 horas pode continuar exposto na view para diagnóstico, mas um item não deve estar pronto apenas porque `refresh_status = FRESH`.

## 13. Contrato do plano diário

Depois da criação do plano deve ser verdadeiro:

```text
planned_total = 112
refreshed_on_planned_date = 112
old_snapshot_count = 0
```

Gate operacional:

```text
112 / 112 D0 -> plano valido
menos de 112 / 112 D0 -> plano invalido
```

## 14. Observabilidade

O relatório do candidate refresh deve distinguir claramente cache diário de freshness por TTL.

Adicionar ou adaptar métricas para representar:

```text
operational_date
same_day_cache_hits
old_date_refresh_candidates
api_calls_attempted
successful_refreshes
failed_refreshes
snapshots_inserted
scoring_candidates_refreshed_today
```

Evitar que uma métrica chamada apenas `fresh_cache_hits` represente a nova regra.

A nova semântica é:

```text
cache hit = ja teve refresh no proprio dia
```

## 15. Limites atuais

Permanecem inalterados:

```text
DISCOVERY_LIMIT = 1000
SCORING_LIMIT = 1000
MAX_API_CALLS = 1000
```

Também permanece a política:

```text
80% ranking
20% exploracao
```

A nova regra apenas pode fazer com que mais candidatos de D-1 consumam chamadas API.

Se `MAX_API_CALLS` for atingido:

```text
deferred_refreshes > 0
-> run_status = partial
```

Candidatos sem snapshot D0 não podem seguir para o planejamento.

## 16. Fora de escopo funcional

Esta mudança não pode alterar:

```text
commercial_score
ScorerAgent
SelectionGate
quotas por subnicho
politica 80/20
112 slots
horarios de dispatch
auto confirmacao de unavailable
ShopeeProvider
cooldown
similarity
ranking comercial
```

A mudança é exclusivamente sobre a validade diária do snapshot.

## 17. Change boundary obrigatório

**Nenhum arquivo fora da lista abaixo pode ser criado, removido, renomeado ou modificado durante a implementação.**

A implementação deve ser rejeitada se o diff contiver qualquer outro arquivo.

### Arquivos autorizados para modificação

1. `src/ofertas_bot/tools/candidate_refresh.py`
   - resolver `operational_date`;
   - trocar a decisão de cache de `refresh_status == FRESH` para snapshot em D0;
   - ajustar métricas do `run_report`;
   - passar `operational_date` ao carregamento pós-refresh;
   - nenhuma outra lógica deve ser refatorada.

2. `src/ofertas_bot/storage/supabase_candidate_refresh_store.py`
   - permitir que `load_scoring_candidates()` receba `operational_date`;
   - restringir scoring a snapshots pertencentes a D0;
   - não alterar persistência de snapshots, `record_success`, `record_failure`, auto confirmação ou discovery SQL além do estritamente necessário.

3. `src/ofertas_bot/tools/plan_daily_dispatch.py`
   - passar `args.date` para `store.load_candidates()`;
   - nenhuma outra alteração permitida.

4. `src/ofertas_bot/storage/supabase_dispatch_plan_store.py`
   - adicionar `planned_date` a `load_candidates()`;
   - substituir o gate operacional baseado apenas em `refresh_status = 'FRESH'` pelo gate de snapshot em `planned_date`;
   - não alterar `replace_day`, advisory lock, regras de proteção contra plano consumido ou persistência dos slots.

### Novo arquivo autorizado

5. `supabase/migrations/202608170001_daily_dispatch_operational_freshness.sql`
   - alterar apenas a view necessária para que `is_ready_for_dispatch` considere snapshot no próprio `planned_date`;
   - migrations antigas não podem ser editadas.

### Arquivos de teste autorizados

6. `tests/test_candidate_refresh_cli.py`
   - adicionar somente os testes necessários à nova regra D0.

7. `tests/test_supabase_dispatch_plan_store.py`
   - adicionar testes para o filtro por `planned_date`.

8. `tests/test_daily_dispatch_migration.py`
   - adicionar teste que valide a nova semântica da view/readiness.

## 18. Arquivos explicitamente proibidos

Entre outros, não podem ser modificados:

```text
src/ofertas_bot/candidate_refresh.py
src/ofertas_bot/daily_dispatch_planner.py
src/ofertas_bot/selection.py
src/ofertas_bot/agents/scorer.py
src/ofertas_bot/providers/shopee.py
config/selection_profiles.toml
scripts/ops/run_shopee_candidate_refresh.sh
deploy/systemd/shopee-candidate-refresh.service
deploy/systemd/shopee-candidate-refresh.timer
n8n/*
docs/*
.env*
pyproject.toml
```

Exceção documental: o próprio arquivo desta spec existe em `docs/specs-nao-implementadas/` e não faz parte do change boundary da implementação de código. O Codex não deve alterar este documento durante a implementação.

Especialmente, `src/ofertas_bot/daily_dispatch_planner.py` não deve ser alterado. Ele já trabalha sobre o universo de candidatos recebido. A garantia D0 deve acontecer antes de os candidatos chegarem ao algoritmo de quotas e sequenciamento.

## 19. Testes obrigatórios

### Candidate refresh

Para `operational_date = 17/08`:

```text
snapshot 17/08 00:01 -> cache_hit
snapshot 17/08 06:00 -> cache_hit
snapshot 16/08 23:59 -> API call
snapshot 16/08 08:00 -> API call
snapshot inexistente -> API call
```

Também validar:

```text
snapshot anterior = D-1
tentativa D0 = technical_failure
-> nao chega ao scoring
```

E:

```text
snapshot anterior = D-1
tentativa D0 = no_node
-> nao chega ao scoring
```

### Planner

Para `planned_date = 17/08`:

```text
snapshot 17/08 -> candidato disponivel
snapshot 16/08 -> candidato excluido
```

Mesmo se o item de 16/08 ainda estiver com `refresh_status = FRESH`, ele deve ser excluído.

### Readiness

Validar:

```text
dispatch_status = planned
is_eligible = true
snapshot_date = planned_date
-> ready = true
```

E:

```text
dispatch_status = planned
is_eligible = true
snapshot_date = D-1
refresh_status = FRESH
-> ready = false
```

## 20. Critérios de aceite

A implementação será considerada concluída somente quando:

1. snapshot de D-1 sempre exigir refresh no job de D0;
2. snapshot de D0 gerar cache hit;
3. falha de refresh em D0 não permitir reaproveitar snapshot de D-1 para scoring;
4. somente snapshots D0 puderem chegar ao planner;
5. nenhum fallback permitir item de D-1;
6. o plano não for completado artificialmente com dados antigos;
7. todos os 112 itens persistidos possuírem snapshot do `planned_date`;
8. readiness usar a data operacional;
9. timezone seja explicitamente `America/Sao_Paulo`;
10. nenhum arquivo fora do change boundary seja modificado.

## 21. Validação final do escopo

Antes de aceitar a implementação, executar:

```bash
git diff --name-only
```

O resultado deve conter somente:

```text
src/ofertas_bot/tools/candidate_refresh.py
src/ofertas_bot/storage/supabase_candidate_refresh_store.py
src/ofertas_bot/tools/plan_daily_dispatch.py
src/ofertas_bot/storage/supabase_dispatch_plan_store.py
supabase/migrations/202608170001_daily_dispatch_operational_freshness.sql
tests/test_candidate_refresh_cli.py
tests/test_supabase_dispatch_plan_store.py
tests/test_daily_dispatch_migration.py
```

Qualquer arquivo adicional no diff significa:

```text
implementacao fora do escopo
-> nao aprovar
```

## 22. Regra final

> Para participar do planejamento e do dispatch do dia D, uma oferta precisa possuir um snapshot obtido no marketplace no próprio dia D, considerando `America/Sao_Paulo`. Snapshot de D-1 é operacionalmente antigo, mesmo que ainda esteja dentro do TTL técnico de 24 horas.

---

# Prompt para o Codex

Use o prompt abaixo sem ampliar o escopo.

```text
Implemente a spec `docs/specs-nao-implementadas/refresh-diario-d0.md` neste repositório.

OBJETIVO
Trocar a validade operacional do refresh usado no planejamento/dispatch diário de uma janela móvel de 24 horas para validade por data operacional D0, sempre em `America/Sao_Paulo`.

REGRA CENTRAL
- Snapshot obtido no próprio dia operacional D0: válido para cache, scoring, planejamento e dispatch.
- Snapshot de D-1 ou anterior: inválido para a operação D0 e deve exigir refresh, mesmo que `refresh_status` ainda seja `FRESH` pelo TTL técnico de 24h.
- O TTL técnico de 24h deve continuar existindo para observabilidade; não o remova nem altere globalmente.

CHANGE BOUNDARY OBRIGATÓRIO
Você pode modificar SOMENTE estes arquivos existentes:
1. `src/ofertas_bot/tools/candidate_refresh.py`
2. `src/ofertas_bot/storage/supabase_candidate_refresh_store.py`
3. `src/ofertas_bot/tools/plan_daily_dispatch.py`
4. `src/ofertas_bot/storage/supabase_dispatch_plan_store.py`
5. `tests/test_candidate_refresh_cli.py`
6. `tests/test_supabase_dispatch_plan_store.py`
7. `tests/test_daily_dispatch_migration.py`

Você pode criar SOMENTE este arquivo novo:
8. `supabase/migrations/202608170001_daily_dispatch_operational_freshness.sql`

NENHUM OUTRO ARQUIVO PODE SER CRIADO, MODIFICADO, REMOVIDO OU RENOMEADO.
Não altere esta spec.
Não faça refactors oportunistas.
Não formate arquivos fora das linhas necessárias.
Não atualize dependências.
Não altere configuração, systemd, scripts ops, n8n, docs, scorer, selection, planner core, provider Shopee ou política 80/20.

IMPLEMENTAÇÃO ESPERADA
1. Em `candidate_refresh.py`:
   - resolva uma `operational_date` em `America/Sao_Paulo`;
   - cache hit somente quando `last_checked_at`, convertido para `America/Sao_Paulo`, pertence a `operational_date`;
   - D-1 ou anterior deve seguir para API;
   - ajuste o relatório para expor a nova semântica de cache diário sem remover informação útil de TTL técnico;
   - passe `operational_date` ao carregamento de candidatos pós-refresh para scoring.

2. Em `supabase_candidate_refresh_store.py`:
   - faça `load_scoring_candidates()` receber `operational_date`;
   - exija que `last_checked_at AT TIME ZONE 'America/Sao_Paulo'` pertença a essa data;
   - um refresh D0 que falhou não pode permitir reaproveitamento do snapshot D-1 para scoring.

3. Em `plan_daily_dispatch.py`:
   - passe `args.date` como `planned_date` para `store.load_candidates()`;
   - não faça outras alterações.

4. Em `supabase_dispatch_plan_store.py`:
   - faça `load_candidates()` receber `planned_date`;
   - mantenha `is_eligible`;
   - exija snapshot em `planned_date` usando explicitamente `America/Sao_Paulo`;
   - não altere `replace_day()` nem lógica de persistência/lock.

5. Na nova migration:
   - ajuste apenas a view necessária de readiness;
   - `is_ready_for_dispatch` deve exigir `dispatch_status = 'planned'`, elegibilidade e snapshot do próprio `planned_date` em `America/Sao_Paulo`;
   - preserve colunas/contratos existentes da view sempre que possível;
   - não edite migrations antigas.

6. Testes:
   - D0 00:01 -> cache hit;
   - D0 06:00 -> cache hit;
   - D-1 23:59 -> API call;
   - D-1 08:00 -> API call;
   - MISSING -> API call;
   - falha técnica em D0 com snapshot D-1 -> não vai para scoring;
   - no_node em D0 com snapshot D-1 -> não vai para scoring;
   - planner aceita snapshot no `planned_date` e exclui D-1 mesmo se TTL técnico ainda for FRESH;
   - readiness true apenas quando snapshot_date == planned_date, além das condições já exigidas.

NÃO ALTERAR
- `src/ofertas_bot/daily_dispatch_planner.py`
- `src/ofertas_bot/candidate_refresh.py`
- ScorerAgent
- SelectionGate
- commercial_score/ranking
- quotas por subnicho
- política 80/20
- horários ou quantidade de slots
- ShopeeProvider
- auto confirmação de unavailable
- scripts systemd/ops
- configurações
- dependências

VALIDAÇÃO OBRIGATÓRIA
Antes de concluir:
1. execute os testes relevantes;
2. execute `git diff --name-only`;
3. confirme que o diff contém SOMENTE os 8 caminhos autorizados;
4. se qualquer outro arquivo aparecer, reverta essa alteração antes de concluir;
5. apresente no resultado final:
   - resumo da mudança;
   - testes executados e resultado;
   - lista exata de arquivos modificados/criados;
   - confirmação explícita de que nenhum arquivo fora do change boundary foi alterado.

Não implemente nada além do descrito nesta spec.
```

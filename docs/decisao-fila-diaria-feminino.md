# Decisao: fila diaria do feminino

Data: 2026-08-13

## Contexto

O grupo `feminino` recebe ofertas em 14 execucoes entre `08h` e `21h`. Antes
desta decisao, cada execucao do n8n buscava os elegiveis do momento. Nao havia
uma grade diaria persistida, nem garantia semanal de cobertura dos subnichos.

## Decisao

A inteligencia de selecao fica antes do n8n. Um planejador le
`offers.v_offer_ranking_current`, aplica a politica versionada e grava 112 slots
em `offers.daily_dispatch_plan`. A view `offers.v_daily_dispatch_ready` expoe
somente o contrato necessario ao envio.

A distribuicao fecha em:

- 96 slots fixos por dia;
- 16 slots rotativos por dia;
- 112 slots rotativos por semana;
- 14 janelas de 8 itens;
- cobertura semanal dos 31 subnichos;
- limite de 2 itens do mesmo subnicho por janela.

## Responsabilidades

O planejador decide score, cotas, rotacao, fallback, diversidade e sequencia.
O n8n consulta a janela corrente, monta a copy, envia para a allowlist e grava
`offers.publication_events`.

Antes do envio, a consulta do n8n reserva os slots com `FOR UPDATE SKIP LOCKED`
e estado `claimed`. Assim, duas execucoes concorrentes nao recebem a mesma
oferta. Cada evento referencia `dispatch_plan_id`; um trigger sincroniza o
estado final como `confirmed`, `failed` ou `cancelled`, e o indice unico impede
que a mesma oferta planejada gere dois eventos.

Em `dry_run`, a view pode ser consultada para previsualizacao, mas o workflow
nao faz claim e nao vincula `dispatch_plan_id`, preservando a fila real.

## Operacao

Gerar primeiro em modo somente leitura:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.plan_daily_dispatch --profile feminino
```

Persistir depois de conferir que o plano tem 112 itens:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.plan_daily_dispatch --profile feminino --apply
```

Um plano pode ser regenerado enquanto todos os seus slots estiverem em
`planned`. Depois que o consumo comecar, a substituicao do dia e bloqueada.

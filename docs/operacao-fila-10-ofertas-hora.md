# Operacao da fila: 10 ofertas por hora

Estado operacional atualizado em 2026-08-26 para o grupo `grupo-ofertas-feminino`.

## Capacidade diaria

A janela de publicacao permanece das 08:00 as 21:00 em `America/Sao_Paulo`, com 14 execucoes por dia.

A capacidade operacional passa a ser:

- 10 ofertas por execucao/hora;
- 14 execucoes por dia;
- 140 ofertas planejadas por dia;
- `slot_sequence` de 1 a 10 por hora;
- `daily_sequence` de 1 a 140 por dia.

O Supabase continua sendo a fonte de verdade da fila, atraves de `offers.daily_dispatch_plan` e da view operacional consumida pelo n8n.

## Configuracao do sender n8n

No workflow `ofertas-mvp-supabase`, o node `Set Contexto Schedule Grupo` deve usar:

```javascript
return [
  {
    json: {
      dry_run: false,
      limit: 10,
      profile: 'feminino',
      marketplace: 'shopee',
      target: 'grupo-ofertas-feminino',
      target_chat_id: '120363412864266334@g.us',
      allowed_targets_csv: 'grupo-ofertas-feminino',
      channel_adapter: 'whatsapp',
      send_delay_seconds_min: 45,
      send_delay_seconds_max: 90,
      coupon_url: 'https://s.shopee.com.br/4AxtmHq4If',
      run_id: new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '-schedule-grupo-real',
    },
  },
];
```

A mudanca funcional em relacao ao estado anterior e somente:

```text
limit: 8 -> limit: 10
```

O limite deve permanecer dentro da validacao ja existente do workflow (`1..20`).

## Estado aplicado em producao

Em 2026-08-26, o `limit` do node `Set Contexto Schedule Grupo` foi alterado manualmente no painel do n8n de `8` para `10`.

Nao e necessario executar deploy automatico do workflow para aplicar esta mudanca, pois a alteracao ja foi realizada manualmente na instancia de producao.

Esta documentacao registra o estado esperado para futuras auditorias e para evitar regressao para `limit=8` em manutencoes posteriores.

## Relacao com o daily dispatch plan

O planner diario deve gerar 140 registros para o perfil `feminino` / marketplace `shopee`, distribuindo 10 registros em cada hora de 08 a 21.

O sender n8n nao define a composicao editorial da fila. Ele consome a janela planejada e o parametro `limit=10` permite consumir os 10 slots previstos para a hora corrente.

A distribuicao editorial, quotas por subnicho, rotacao e fallback permanecem fora do n8n e sao definidos pelo planner/configuracao de selecao.

## Validacao operacional

Depois de uma execucao horaria normal, a verificacao esperada no Supabase e:

- ate 10 registros da hora consumidos/confirmados conforme resultado do envio;
- `slot_sequence` podendo chegar a 10;
- ausencia do padrao sistematico de slots 9 e 10 permanecendo `planned` por causa de limite do sender.

Nao recuperar manualmente janelas de horarios ja encerrados apenas por causa da alteracao de capacidade. A mudanca vale para as execucoes seguintes.

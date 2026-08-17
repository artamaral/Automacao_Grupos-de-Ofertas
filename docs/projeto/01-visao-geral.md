# Visao geral

## Objetivo do MVP

Colocar em operacao minima uma esteira propria de ofertas usando o que ja esta
validado:

- catalogos ativos no Supabase;
- ranking e elegibilidade em `offers.v_offer_ranking_current`;
- n8n como orquestrador e executor do disparo;
- allowlist explicita de destinos;
- historico de envios em `offers.publication_events`.

O objetivo nao e fechar a arquitetura final. O objetivo e provar o ciclo
operacional mais curto possivel antes de ampliar automacao, coleta e regras de
nicho.

## Pipeline principal

```text
Catalogo ativo no Supabase
  -> n8n consulta ranking
  -> n8n monta mensagem
  -> n8n envia para allowlist
  -> Supabase registra historico
```

## Regra operacional atual

- Supabase e a base operacional do catalogo publicado.
- n8n consulta o Supabase diretamente, sem worker intermediario no MVP.
- n8n monta `message_text` com template simples controlado no workflow ou em
  configuracao segura do proprio n8n.
- n8n so pode enviar para destinos explicitamente allowlisted.
- O registro de tentativa e resultado volta para `offers.publication_events`.
- Descoberta, limpeza e curadoria de catalogo continuam fora da rodada diaria.

## Fora do MVP

- Cloud Run como executor principal.
- Coleta automatica para atualizar catalogos.
- Revisao semantica completa dos nichos e subnichos.
- Regras finas de roteamento por grupo.
- Revisao humana item a item obrigatoria.
- Integracao real Shopee/Amazon dentro da rodada diaria.

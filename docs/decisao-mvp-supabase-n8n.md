# Decisao de arquitetura MVP Supabase e n8n

## Evolucao vigente para feminino

O fluxo direto pelo ranking permanece como registro do MVP inicial, mas deixou
de ser o contrato de selecao do grupo `feminino`. A operacao atual prepara uma
fila diaria persistida antes do n8n:

```text
shopee-candidate-refresh.timer (07:00 BRT)
  -> refresh/rechecagem Shopee
  -> planejador de bandas e rotacao
  -> offers.daily_dispatch_plan
  -> offers.v_daily_dispatch_ready
  -> n8n monta, envia e registra publication_events
```

Refresh e planejamento pertencem ao mesmo service `systemd` e ao mesmo lock.
O planejamento so comeca depois que o refresh e sua pos-etapa opcional terminam
com sucesso; nao existe um segundo agendamento para gerar a fila.

O n8n executa de hora em hora entre `08h` e `21h` e consome `8` slots prontos.
Ele nao decide banda, rotacao, fallback ou ordenacao diaria. O vinculo
`publication_events.dispatch_plan_id` controla o consumo idempotente do slot.

Este documento e a decisao canonica do MVP operacional.

Estado observado como padrao vigente em `2026-08-14`:

- o `feminino` opera por `offers.daily_dispatch_plan` e
  `offers.v_daily_dispatch_ready`;
- o planejador carrega candidatos apenas de `offers.v_offer_ranking_current`
  com `is_eligible = true`;
- `offers.publication_events` e a prova operacional de envio confirmado, mas
  nao atua sozinho como trava ativa de anti-repost no caminho atual;
- `offers.offer_selection_state` existe no schema e participa da view de
  ranking, mas seus campos `selected_at`, `cooldown_until` e `last_sent_at`
  nao estao governando o repost do `feminino` no estado real atual;
- tudo que dependia do fluxo direto `ranking -> n8n -> anti-repost por query`
  deve ser lido como legado.

## Fluxograma vigente: refresh, ordenacao e publicacao

```mermaid
flowchart TD
    A[07:00 BRT: timer diario] --> B[Refresh comercial dos candidatos]
    B --> C{Resultado do refresh}
    C -->|snapshot atualizado| D[v_offer_ranking_current recalcula dados e score]
    C -->|no_node repetido e confirmado| E[Item fica indisponivel]
    C -->|falha sem confirmacao| D

    D --> F{Filtros de elegibilidade}
    F -->|rating menor que 4.8| X[Item fora do plano]
    F -->|preco invalido ou link ausente| X
    F -->|similarity_status = suppressed| X
    F -->|cooldown_until no futuro| X
    F -->|item saudavel| G[Conjunto elegivel]

    G --> H[Ordenacao deterministica por score, vendas, rating e item_id]
    H --> I[Aplicacao das cotas fixas e da rotacao semanal]
    I --> J[Distribuicao em 14 janelas de 8 itens]
    J --> K[daily_dispatch_plan do dia]
    K --> L[v_daily_dispatch_ready]
    L --> M[n8n envia para destino allowlisted]
    M --> N[publication_events registra o resultado]
    N --> O[Trigger consome apenas o slot daquele dia]

    O -. nao atualiza selected_at,<br/>last_sent_at ou cooldown_until .-> P[LACUNA: item continua elegivel]
    P --> Q[Planejamento do dia seguinte]
    Q --> H
```

O refresh nao e uma descoberta de novos produtos nem uma regra de diversidade.
Ele revalida os dados comerciais dos candidatos existentes e pode retirar um
item que deixou de ser comercialmente valido. Se o produto continuar saudavel,
o refresh preserva sua capacidade de competir pelo topo do ranking.

A ordenacao usada para carregar candidatos e estavel: `commercial_score desc`,
`sales_count desc`, `rating desc nulls last` e `item_id`. Em seguida, o
planejador escolhe os primeiros itens de cada subnicho conforme as cotas e os
espalha pelas janelas. A data altera a parcela da rotacao semanal, mas nao cria
uma penalidade para o item publicado no dia anterior.

## Lacuna de diversidade entre dias

As travas atuais respondem a pergunta "o item esta saudavel para publicar?",
mas nao respondem a pergunta "este item foi publicado recentemente?". A coluna
`cooldown_until` participa de `is_eligible` e a configuracao declara um cooldown
padrao de `24` horas, porem o fluxo vigente nao preenche `cooldown_until`,
`selected_at` ou `last_sent_at` depois da confirmacao em `publication_events`.
Assim, a regra existe no modelo, mas nao fecha o ciclo operacional.

Leitura real do banco em `2026-08-14`, sem escrita:

- os planos de `2026-08-13` e `2026-08-14` tinham `112` itens cada e
  compartilhavam `110` itens (`98,2%`);
- dos `77` itens com envio confirmado em `2026-08-13`, `62` reapareceram no
  plano de `2026-08-14`;
- ate o momento da consulta, `16` itens tinham envio confirmado em
  `2026-08-14`, todos ainda apareciam como elegiveis e `2` ja haviam sido
  confirmados tambem no dia anterior;
- uma simulacao somente em memoria do plano de `2026-08-15`, usando o ranking
  atual, repetiu `110` dos `112` itens do plano de `2026-08-14`.

A simulacao nao e uma previsao exata do plano seguinte, pois o proximo refresh
pode alterar disponibilidade, preco e score. Ela mede a exposicao estrutural:
se os produtos continuarem saudaveis e bem ranqueados, quase nada no algoritmo
atual os faz ceder lugar a outros produtos elegiveis do mesmo subnicho.

Essa lacuna e importante porque a fila diaria garante unicidade apenas dentro
do mesmo `planned_date`. Ela impede duplicar um item no mesmo plano e impede
consumir duas vezes o mesmo slot, mas nao impede repetir o mesmo `stable_key` em
datas consecutivas. Com cotas fixas e ordenacao deterministica, o topo de cada
subnicho tende a se cristalizar, reduzindo variedade para o publico e deixando
grande parte do catalogo saudavel sem exposicao.

Ele substitui, para a fase atual, a leitura anterior baseada em Supabase +
Cloud Run. Cloud Run permanece como evolucao futura ou ponte tecnica opcional,
mas nao e requisito para colocar o MVP em operacao.

## Decisao registrada

O fluxo oficial do MVP para `feminino` passa a ser:

```text
Catalogo ativo no Supabase
  -> cron atualiza snapshots e persiste a fila diaria
  -> n8n consulta offers.v_daily_dispatch_ready
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
- fila diaria persistida;
- historico de tentativas e envios.

### n8n

n8n e o orquestrador do MVP para:

- iniciar a rodada;
- consultar a janela corrente em `offers.v_daily_dispatch_ready`;
- consumir ate `8` slots planejados por rodada;
- montar `message_text`;
- validar allowlist de destino;
- enviar pelo canal configurado;
- gravar resultado em `offers.publication_events`.

Hospedagem proposta para o MVP:

- n8n self-hosted em VPS da Hostinger;
- acesso operacional ao servidor via VSCode Remote SSH;
- credenciais, `.env`, chaves, sessoes, QR codes e tokens ficam apenas na VPS
  ou no painel seguro do servico correspondente;
- o repositorio versiona workflow exportavel, payloads de exemplo,
  documentacao e scripts de apoio, mas nao segredos.

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

## Contrato legado da query MVP

Antes da fila persistida, o n8n consultava `offers.v_offer_ranking_current` com
filtros explicitos e excluia ofertas ja confirmadas para o mesmo destino logico
e canal. Isso evitava repostar o mesmo `stable_key` quando o topo do ranking
permanecia igual entre rodadas.

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
from offers.v_offer_ranking_current ranking
where ranking.is_eligible = true
  and ranking.profile = :profile
  and ranking.marketplace = :marketplace
  and not exists (
    select 1
    from offers.publication_events event
    where event.profile = ranking.profile
      and event.marketplace = ranking.marketplace
      and event.stable_key = ranking.stable_key
      and event.target = :target
      and event.channel_adapter = :channel_adapter
      and event.delivery_status = 'confirmed'
  )
order by
  rank_profile nulls last,
  commercial_score desc,
  sales_count desc,
  rating desc nulls last,
  item_id
limit :limit;
```

`delivery_status = 'confirmed'` era a fronteira anti-repost do MVP inicial.
Dry-runs e bloqueios de allowlist gravados como `cancelled` nao removiam a
oferta do ranking futuro.

Essa query permanece como registro historico, nao como contrato vigente do
`feminino`. O workflow atual nao deve voltar a selecionar diretamente do
ranking nem ser descrito como se ainda aplicasse essa trava no caminho real.

## Perdas de escopo e feature no estado atual

Ao migrar do fluxo direto por query para a fila diaria persistida, o projeto
ganhou previsibilidade operacional, mas perdeu capacidades que existiam ou
estavam implicitas no desenho anterior:

- a trava anti-repost por `publication_events.confirmed` deixou de ser aplicada
  diretamente na query de selecao do caminho vigente;
- a selecao deixou de considerar `target` e `channel_adapter` no momento do
  ranking, entao o bloqueio por destino/canal passou a depender de outra camada
  que hoje nao esta fechada no caminho principal;
- `offers.offer_selection_state` continua no modelo, mas nao fecha hoje o ciclo
  de `selected_at`, `cooldown_until`, `last_sent_at` e `selection_count` apos
  envio confirmado;
- a arquitetura atual protege muito bem o consumo idempotente do slot diario,
  mas protege pior a reentrada futura do mesmo item no ranking do `feminino`;
- a camada de similaridade continua operante, porem hoje tambem mascara parte
  da contaminacao semantica da taxonomia do `feminino`, o que reduz a clareza
  entre "duplicidade legitima" e "item fora do perfil".

Essas perdas nao invalidam o fluxo atual. Elas apenas registram que o estado
vigente ficou mais enxuto do que o desenho anterior e ainda nao recompôs todas
as travas de elegibilidade e anti-repost prometidas historicamente.

## Seguranca do MVP

- Credenciais ficam no n8n/Supabase, nunca no Git.
- O envio real so pode acontecer para destinos em allowlist.
- O workflow deve bloquear destino ausente da allowlist.
- O texto deve conter disclosure de afiliado.
- O registro em `publication_events` deve ser idempotente.
- O anti-repost por `target` e `channel_adapter` continua como requisito
  desejado do MVP, mas nao deve ser descrito como comportamento ativo do caminho
  vigente do `feminino` enquanto a trava nao estiver recolocada no fluxo real.

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

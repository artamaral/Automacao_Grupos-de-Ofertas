# Spec — Rastreamento de cliques, conversões e valor por exposição na Shopee

Status: especificação funcional e técnica para instrumentação de tracking e base analítica. As regras comerciais/editoriais existentes permanecem preservadas. `product_type` editorial continua como evolução futura.

## 1. Objetivo de negócio

O objetivo não é replicar os relatórios da Shopee no Supabase. O objetivo é responder, com evidência, quanto valor cada exposição do grupo produziu e o que isso ensina sobre o próximo produto que merece ocupar um slot.

A unidade canônica de análise é a exposição planejada:

```text
offers.daily_dispatch_plan.dispatch_plan_id
```

A arquitetura deve permitir a cadeia:

```text
exposição planejada
→ publicação
→ raw clicks
→ conversões
→ pedidos
→ itens comprados
→ comissão
```

Perguntas centrais:

1. qual exposição/publicação merece ocupar espaço no grupo;
2. quais exposições geram interesse, medido por clique;
3. quais exposições geram monetização;
4. a venda foi do mesmo produto anunciado ou de outro produto;
5. quanto `totalCommission` cada exposição produziu;
6. quais subnichos consomem slots e qual retorno produzem;
7. futuramente, se existe saturação por tipo funcional mesmo com `item_id` diferentes.

O `commercial_score` atual não deve ser alterado por esta spec.

## 2. Orquestração diária

Hoje existem caminhos separados para refresh e planejamento diário. A evolução deve criar uma única orquestração sequencial:

```text
1. Refresh Shopee existente
   ↓
2. Planner diário existente
   ↓
3. Geração das short URLs rastreáveis
   ↓
4. Liberação da fila para consumo/publicação
```

A consolidação é apenas de orquestração. Refresh e planner continuam componentes independentes e testáveis.

### 2.1 Não alterar no refresh

- critérios de candidatos;
- políticas/limites;
- `FRESH`/`STALE`;
- snapshots;
- estabilidade;
- scoring;
- elegibilidade.

### 2.2 Não alterar no planner

- `commercial_score` e seus pesos;
- quotas;
- distribuição editorial;
- rotação;
- fallback;
- cooldown;
- taxonomia/subnichos;
- número de slots;
- horários/sequenciamento;
- regras atuais de persistência/substituição do plano.

### 2.3 Não alterar no publicador/n8n

- copy existente;
- allowlist;
- grupo/destino WhatsApp;
- WAHA;
- regras atuais de claim, consumo e registro do envio.

A única mudança de contrato de dados para a copy é que o mesmo campo `offer_link` passa a expor a short URL específica da exposição.

## 3. Identidade e tracking pré-publicação

O `dispatch_plan_id` é a identidade canônica pré-publicação. O `publish_id` continua sendo a identidade do evento de publicação registrado depois do envio.

### 3.1 URL de entrada

A entrada `originUrl` de `generateShortLink` deve ser:

```text
offers.catalog_items.product_link
```

Não usar `catalog_items.offer_link` como origem da nova chamada.

### 3.2 URL usada pela copy

Fluxo:

```text
catalog_items.product_link
        ↓ originUrl
generateShortLink
        ↓ shortLink
daily_dispatch_plan.tracking_short_url
        ↓ projetada como offer_link
v_daily_dispatch_ready
        ↓
n8n / copy / WhatsApp
```

A short URL é propriedade da exposição planejada. **Não sobrescrever globalmente `catalog_items.offer_link`** com link contendo tracking de um `dispatch_plan_id` específico.

### 3.3 Quatro Sub IDs obrigatórios

| Posição | Conteúdo | Regra | Exemplo |
| --- | --- | --- | --- |
| `subId[0]` | meio | literal deste fluxo | `wa` |
| `subId[1]` | perfil | `daily_dispatch_plan.profile` sem mapping manual | `feminino` |
| `subId[2]` | exposição | `dp` + UUID sem hífens | `dp550e8400e29b41d4a716446655440000` |
| `subId[3]` | produto anunciado | `daily_dispatch_plan.item_id` como texto | `18797641257` |

A quinta posição permanece reservada.

Normalização:

```text
550e8400-e29b-41d4-a716-446655440000
→ 550e8400e29b41d4a716446655440000
→ dp550e8400e29b41d4a716446655440000
```

Regra:

```text
dispatch_tracking_id = "dp" + replace(dispatch_plan_id::text, "-", "")
```

Não usar hífen, underscore, truncamento ou hash.

Esse formato completo foi aceito em teste real de `generateShortLink`.

### 3.4 Exemplo validado

```graphql
mutation {
  generateShortLink(input: {
    originUrl: "https://shopee.com.br/Sand%C3%A1lia-Feminina-Vizzano-Salto-Bloco-Baixo-Grosso-B%C3%A1sica-4cm-Saltinho-ORIGINAL-i.448506781.18797641257?extraParams=%7B%22display_model_id%22%3A199180557225%2C%22model_selection_logic%22%3A3%7D",
    subIds: [
      "wa",
      "feminino",
      "dp550e8400e29b41d4a716446655440000",
      "18797641257"
    ]
  }) {
    shortLink
    longLink
  }
}
```

Short URL observada:

```text
https://s.shopee.com.br/3g3DPzjYgO
```

### 3.5 Precondições para READY

Uma exposição Shopee só pode ficar pronta quando:

- existir `product_link`;
- existir `profile`;
- existir `dispatch_plan_id`;
- existir `item_id`;
- os quatro Sub IDs forem produzidos conforme o contrato;
- `generateShortLink` retornar `shortLink` válida;
- a short URL for persistida para o plano.

Não existe fallback silencioso para URL sem tracking.

## 4. Fontes externas e para que cada uma serve

### 4.1 Click Report CSV — interesse/raw clicks

O Click Report não está na Open API observada. Ele é obtido pelo Portal/Central do Afiliado e importado posteriormente.

O CSV já fornecido possui:

- `ID dos Cliques`;
- `Tempo dos Cliques`;
- `Região dos Cliques`;
- `Sub_id`;
- `Referenciador`.

O arquivo histórico analisado possui 48 raw clicks e `Sub_id = ----` em todos; esses registros permanecem válidos como tráfego bruto, mas não podem ser atribuídos deterministicamente a um plano.

A documentação oficial da Shopee confirma que o Relatório de Cliques pode ser exportado e analisado por `Sub_id(s)` e orienta separar os Sub IDs em colunas no Excel. Portanto a arquitetura **pode depender documentalmente da presença dos Sub IDs no relatório**.

Fonte oficial verificada: [Como acompanhar o número de cliques nos seus links](https://help.shopee.com.br/portal/10/article/127718-Como-acompanhar-o-n%C3%BAmero-de-cliques-nos-seus-links?previousPage=related+articles).

O teste empírico em andamento não decide se os Sub IDs existem; ele servirá apenas para confirmar a **serialização/delimitador concreto no CSV** e validar o parser.

Até o novo CSV:

- preservar sempre `Sub_id` bruto;
- não fixar delimitador;
- não fixar parser baseado em hipótese.

A documentação oficial apresenta `ID dos Cliques` como campo/filtro do relatório, mas não foi encontrada garantia de unicidade global. Portanto `click_id` deve ser indexado, mas **não deve receber constraint `UNIQUE` nesta fase**.

### 4.2 `conversionReport` — conversões e valor observado

A query de referência fornecida retorna no nível da conversão:

- `clickTime`;
- `purchaseTime`;
- `conversionId`;
- `shopeeCommissionCapped`;
- `sellerCommission`;
- `totalCommission`;
- `netCommission`;
- `mcnManagementFeeRate`;
- `mcnManagementFee`;
- `mcnContractId`;
- `linkedMcnName`;
- `buyerType`;
- `utmContent`;
- `device`;
- `productType`;
- `referrer`.

Pedidos retornam `orderId`, `shopType`, `orderStatus` e itens com `itemId`, `itemName`, valores, comissão, categorias, fraude, `attributionType` e demais campos do payload fornecido.

A paginação retorna `page`, `limit`, `hasNextPage`, `scrollId`.

O `productId` usado na query de exemplo é fictício e não deve virar constante/default.

`clickTime` aqui representa o clique da conversão e não substitui o Click Report para o universo de raw clicks.

### 4.3 KPI econômico principal

Decisão fechada:

```text
KPI econômico principal = totalCommission
```

Motivo operacional: `totalCommission` representa a soma observada das parcelas de comissão retornadas no relatório. Exemplo real fornecido:

```text
shopeeCommissionCapped = 1.6542
sellerCommission       = 30.8784
totalCommission        = 32.5326
```

`netCommission` continua armazenado para reconciliação, mas não é o KPI principal de valor por slot desta fase.

### 4.4 Venda direta versus indireta

A documentação oficial da Shopee define:

- **direta**: compra do mesmo produto divulgado;
- **indireta**: compra de produto diferente do divulgado.

Fonte oficial verificada: [Como funcionam as atribuições: vendas diretas ou indiretas](https://help.shopee.com.br/portal/10/article/163055-Como-funcionam-as-atribui%C3%A7%C3%B5es%3A-vendas-diretas-ou-indiretas?previousPage=related+articles).

Portanto a classificação interna não depende de loja:

```text
advertised_item_id = daily_dispatch_plan.item_id
purchased_item_id  = conversionReport.orders.items.itemId

advertised_item_id = purchased_item_id  → direct
advertised_item_id <> purchased_item_id → indirect
```

Não é necessário obter `shop_id` do produto anunciado para responder essa pergunta. `shopId` do item comprado pode continuar no raw payload/coluna auxiliar, mas não é requisito da classificação direta/indireta.

`attributionType` permanece armazenado como evidência externa e pode ser comparado com a classificação derivada, mas a regra principal acima já está suportada documentalmente.

Exemplo real fornecido também mostrou `attributionType = ORDERED_IN_SAME_SHOP`; esse valor deve ser preservado, não reinterpretado além do contrato documentado.

### 4.5 `validatedReport` — reconciliação financeira posterior

A documentação oficial da Shopee confirma que, após o pedido ficar `Concluído`, a comissão passa por validação e as comissões validadas representam valores cujo recebimento está assegurado.

Fonte oficial verificada: [Entenda o processo de validação das comissões](https://help.shopee.com.br/portal/10/article/163057-Entenda-o-Processo-de-Valida%C3%A7%C3%A3o-das-Comiss%C3%B5es).

Na Open API/Playground observado pelo projeto, `validatedReport` requer `validationId`. O resultado real de `conversionReport` fornecido contém `conversionId` e `orderId`, mas não apresentou `validationId`.

**Pendência:** identificar, em fonte oficial/API disponível à conta, como obter programaticamente o `validationId` requerido.

Até isso ser resolvido:

- `validatedReport` não bloqueia a implementação de tracking, raw clicks e `conversionReport`;
- a primeira camada analítica usa Click Report + `conversionReport`;
- `validatedReport` entra como reconciliação financeira posterior;
- não inventar ligação `conversionId → validationId`.

## 5. Princípio de modelagem do banco

O banco é orientado a decisão de negócio:

1. `dispatch_plan_id` é a identidade da exposição;
2. não duplicar em clique/conversão dados recuperáveis do plano;
3. preservar raw externo para auditoria e reprocessamento;
4. promover a coluna apenas o que participa das análises principais;
5. separar item anunciado de item comprado;
6. preservar proveniência de `conversionReport` e futuramente `validatedReport`;
7. não replicar integralmente o schema externo.

## 6. Schema proposto

### 6.1 Alterações em `offers.daily_dispatch_plan`

**Fonte:** processo interno + `generateShortLink`.

| Coluna | Tipo sugerido | Uso |
| --- | --- | --- |
| `tracking_sub_ids` | `TEXT[] NULL` | quatro Sub IDs enviados |
| `tracking_short_url` | `TEXT NULL` | URL efetiva da exposição |
| `tracking_generated_at` | `TIMESTAMPTZ NULL` | auditoria |
| `tracking_status` | `TEXT NOT NULL DEFAULT 'pending'` | `pending/ready/failed` |
| `tracking_error` | `TEXT NULL` | diagnóstico técnico |

Regras: exatamente quatro Sub IDs e short URL não nula quando `tracking_status='ready'`; `v_daily_dispatch_ready.offer_link` deve projetar `tracking_short_url` para Shopee.

### 6.2 `offers.shopee_click_report_imports`

**Fonte:** CSV baixado do Portal do Afiliado.

| Coluna | Tipo sugerido |
| --- | --- |
| `import_id` | `UUID PK` |
| `source_filename` | `TEXT NOT NULL` |
| `source_sha256` | `TEXT NOT NULL UNIQUE` |
| `downloaded_at` | `TIMESTAMPTZ NULL` |
| `imported_at` | `TIMESTAMPTZ NOT NULL` |
| `row_count` | `INTEGER NOT NULL` |
| `status` | `TEXT NOT NULL` |
| `error` | `TEXT NULL` |
| `created_at` | `TIMESTAMPTZ NOT NULL` |

### 6.3 `offers.shopee_click_events`

**Fonte:** uma linha do Click Report.

| Coluna | Tipo sugerido | Origem/uso |
| --- | --- | --- |
| `click_event_id` | `UUID PK` | chave técnica interna |
| `import_id` | `UUID NOT NULL FK` | lote |
| `click_id` | `TEXT NOT NULL` | `ID dos Cliques`; indexar, não declarar UNIQUE ainda |
| `click_time` | `TIMESTAMPTZ NOT NULL` | `Tempo dos Cliques` |
| `click_region` | `TEXT NULL` | raw secundário |
| `sub_id_raw` | `TEXT NULL` | raw obrigatório |
| `referrer` | `TEXT NULL` | raw secundário |
| `dispatch_plan_id` | `UUID NULL FK` | resolvido do tracking |
| `advertised_item_id_raw` | `BIGINT NULL` | quarto Sub ID, para consistência |
| `tracking_parse_status` | `TEXT NOT NULL` | `unparsed/resolved/unrecognized/legacy_empty` |
| `tracking_parse_error` | `TEXT NULL` | diagnóstico |
| `raw_row` | `JSONB NOT NULL` | linha original |
| `created_at` | `TIMESTAMPTZ NOT NULL` | auditoria |

Não duplicar `profile`, subnicho, score ou slot; todos vêm do plano após resolver `dispatch_plan_id`.

### 6.4 `offers.shopee_conversion_sync_runs`

**Fonte:** execução/paginação da API.

| Coluna | Tipo sugerido |
| --- | --- |
| `sync_run_id` | `UUID PK` |
| `report_type` | `TEXT NOT NULL` |
| `query_filters` | `JSONB NOT NULL` |
| `started_at` | `TIMESTAMPTZ NOT NULL` |
| `finished_at` | `TIMESTAMPTZ NULL` |
| `status` | `TEXT NOT NULL` |
| `nodes_received` | `INTEGER NOT NULL DEFAULT 0` |
| `last_page` | `INTEGER NULL` |
| `page_limit` | `INTEGER NULL` |
| `has_next_page` | `BOOLEAN NULL` |
| `last_scroll_id` | `TEXT NULL` |
| `error` | `TEXT NULL` |
| `created_at` | `TIMESTAMPTZ NOT NULL` |

Nesta primeira fase, `report_type='conversion_report'`. `validated_report` entra quando o fluxo de `validationId` estiver definido.

### 6.5 `offers.shopee_conversions`

**Fonte:** `conversionReport.nodes[]` e futuramente `validatedReport.nodes[]`.

| Coluna | Tipo sugerido | Uso |
| --- | --- | --- |
| `conversion_id` | `TEXT PK` | identidade externa |
| `dispatch_plan_id` | `UUID NULL FK` | resolvido de `utmContent` |
| `utm_content_raw` | `TEXT NULL` | raw de tracking |
| `click_time` | `TIMESTAMPTZ NULL` | clique convertido |
| `purchase_time` | `TIMESTAMPTZ NULL` | compra |
| `buyer_type` | `TEXT NULL` | segmentação futura |
| `total_commission` | `NUMERIC NULL` | **KPI econômico principal** |
| `net_commission` | `NUMERIC NULL` | reconciliação |
| `seller_commission` | `NUMERIC NULL` | composição |
| `shopee_commission_capped` | `NUMERIC NULL` | composição |
| `first_seen_at` | `TIMESTAMPTZ NOT NULL` | auditoria |
| `last_seen_at` | `TIMESTAMPTZ NOT NULL` | auditoria |
| `created_at` | `TIMESTAMPTZ NOT NULL` | auditoria |
| `updated_at` | `TIMESTAMPTZ NOT NULL` | auditoria |

### 6.6 `offers.shopee_conversion_observations`

Serve para preservar o node bruto por execução e, futuramente, comparar `conversionReport` com `validatedReport`.

| Coluna | Tipo sugerido |
| --- | --- |
| `observation_id` | `UUID PK` |
| `conversion_id` | `TEXT NOT NULL FK` |
| `sync_run_id` | `UUID NOT NULL FK` |
| `report_type` | `TEXT NOT NULL` |
| `observed_at` | `TIMESTAMPTZ NOT NULL` |
| `total_commission` | `NUMERIC NULL` |
| `net_commission` | `NUMERIC NULL` |
| `seller_commission` | `NUMERIC NULL` |
| `shopee_commission_capped` | `NUMERIC NULL` |
| `raw_payload` | `JSONB NOT NULL` |

Campos secundários como MCN, `device`, `productType` e `referrer` permanecem no raw nesta fase, salvo necessidade analítica posterior.

### 6.7 `offers.shopee_conversion_orders`

**Fonte:** `nodes[].orders[]`.

| Coluna | Tipo sugerido |
| --- | --- |
| `conversion_order_id` | `UUID PK` |
| `conversion_id` | `TEXT NOT NULL FK` |
| `order_id` | `TEXT NOT NULL` |
| `shop_type` | `TEXT NULL` |
| `order_status` | `TEXT NULL` |
| `first_seen_at` | `TIMESTAMPTZ NOT NULL` |
| `last_seen_at` | `TIMESTAMPTZ NOT NULL` |
| `raw_payload` | `JSONB NULL` |

Chave natural proposta para estado corrente: `conversion_id + order_id`.

### 6.8 `offers.shopee_conversion_items`

**Fonte:** `nodes[].orders[].items[]`.

| Coluna | Tipo sugerido | Uso |
| --- | --- | --- |
| `conversion_item_id` | `UUID PK` | técnica |
| `conversion_id` | `TEXT NOT NULL FK` | conversão |
| `order_id` | `TEXT NOT NULL` | pedido |
| `item_id` | `BIGINT NOT NULL` | item comprado |
| `item_name` | `TEXT NULL` | leitura/auditoria |
| `item_price` | `NUMERIC NULL` | referência |
| `actual_amount` | `NUMERIC NULL` | valor efetivo |
| `refund_amount` | `NUMERIC NULL` | ajuste |
| `qty` | `INTEGER NULL` | quantidade |
| `item_total_commission` | `NUMERIC NULL` | comissão do item |
| `global_category_lv1_name` | `TEXT NULL` | demanda comprada |
| `global_category_lv2_name` | `TEXT NULL` | demanda comprada |
| `global_category_lv3_name` | `TEXT NULL` | demanda comprada |
| `fraud_status` | `TEXT NULL` | integridade |
| `attribution_type` | `TEXT NULL` | evidência Shopee |
| `complete_time` | `TIMESTAMPTZ NULL` | ciclo do pedido |
| `raw_payload` | `JSONB NOT NULL` | item completo original |

`shopId`, `shopName`, campanhas, taxas adicionais, `promotionId`, `modelId` e demais campos fornecidos pela API ficam preservados em `raw_payload` nesta fase porque não são necessários para responder direta versus indireta.

### 6.9 Diagrama lógico

```text
daily_dispatch_plan
  PK dispatch_plan_id
  item_id anunciado
  primary_subniche
  commercial_score
  tracking_short_url
  tracking_sub_ids
       │
       ├──── 0..1 publication_events
       ├──── 0..N shopee_click_events
       └──── 0..N shopee_conversions
                    ├──── 0..N conversion_observations
                    └──── 1..N conversion_orders
                                  └──── 1..N conversion_items
                                             item_id comprado

shopee_click_report_imports → proveniência/idempotência do CSV
shopee_conversion_sync_runs → proveniência/paginação da API
```

## 7. Queries analíticas prioritárias

As queries abaixo expressam o contrato de negócio; nomes finais podem ser ajustados na migração.

### 7.1 Valor por exposição — KPI principal `totalCommission`

```sql
with clicks as (
  select dispatch_plan_id, count(*) as clicks, min(click_time) as first_click_at
  from offers.shopee_click_events
  where dispatch_plan_id is not null
  group by dispatch_plan_id
), conv as (
  select dispatch_plan_id,
         count(*) as conversions,
         sum(coalesce(total_commission, 0)) as total_commission
  from offers.shopee_conversions
  where dispatch_plan_id is not null
  group by dispatch_plan_id
)
select
  p.dispatch_plan_id,
  p.planned_date,
  p.planned_hour,
  p.daily_sequence,
  p.item_id as advertised_item_id,
  p.primary_subniche,
  p.commercial_score,
  pe.sent_at,
  coalesce(cl.clicks, 0) as clicks,
  coalesce(cv.conversions, 0) as conversions,
  coalesce(cv.total_commission, 0) as total_commission,
  case when coalesce(cl.clicks, 0) > 0
       then cv.total_commission / cl.clicks end as total_commission_per_click,
  cl.first_click_at - pe.sent_at as time_to_first_click
from offers.daily_dispatch_plan p
left join offers.publication_events pe on pe.dispatch_plan_id = p.dispatch_plan_id
left join clicks cl on cl.dispatch_plan_id = p.dispatch_plan_id
left join conv cv on cv.dispatch_plan_id = p.dispatch_plan_id
where p.marketplace = 'shopee';
```

### 7.2 Performance por subnicho

Pergunta: quantos slots o subnicho consome e quanto `totalCommission` produz por exposição?

Implementar preferencialmente sobre uma view agregada por `dispatch_plan_id` para evitar multiplicação em joins 1:N.

### 7.3 Venda direta versus indireta

```sql
select
  c.dispatch_plan_id,
  p.item_id as advertised_item_id,
  i.item_id as purchased_item_id,
  case
    when i.item_id = p.item_id then 'direct'
    else 'indirect'
  end as sale_type,
  i.attribution_type,
  i.actual_amount,
  i.item_total_commission,
  i.global_category_lv1_name,
  i.global_category_lv2_name,
  i.global_category_lv3_name
from offers.shopee_conversions c
join offers.daily_dispatch_plan p on p.dispatch_plan_id = c.dispatch_plan_id
join offers.shopee_conversion_items i on i.conversion_id = c.conversion_id;
```

### 7.4 Produtos anunciados que geram mais venda indireta

```sql
select
  p.item_id as advertised_item_id,
  count(distinct p.dispatch_plan_id) as exposures,
  count(distinct c.conversion_id) as conversions,
  count(*) filter (where i.item_id <> p.item_id) as indirect_item_lines,
  sum(i.item_total_commission) filter (where i.item_id <> p.item_id)
    as indirect_total_commission
from offers.daily_dispatch_plan p
join offers.shopee_conversions c on c.dispatch_plan_id = p.dispatch_plan_id
join offers.shopee_conversion_items i on i.conversion_id = c.conversion_id
group by p.item_id
order by indirect_total_commission desc nulls last;
```

### 7.5 Categorias efetivamente compradas

```sql
select
  i.global_category_lv1_name,
  i.global_category_lv2_name,
  i.global_category_lv3_name,
  count(*) as purchased_item_lines,
  sum(coalesce(i.qty, 0)) as units,
  sum(coalesce(i.actual_amount, 0)) as actual_amount,
  sum(coalesce(i.item_total_commission, 0)) as total_commission
from offers.shopee_conversion_items i
join offers.shopee_conversions c on c.conversion_id = i.conversion_id
where c.dispatch_plan_id is not null
group by 1,2,3
order by total_commission desc nulls last;
```

### 7.6 Funil publicação → raw click → conversão

Usar `publication_events`, clicks atribuídos por `dispatch_plan_id` e conversões atribuídas pelo mesmo plano. `clicks_per_publication` não deve ser chamado CTR enquanto não houver impressão individual confiável.

### 7.7 Latência

```sql
select
  c.conversion_id,
  c.dispatch_plan_id,
  pe.sent_at,
  c.click_time,
  c.purchase_time,
  c.click_time - pe.sent_at as publication_to_converted_click,
  c.purchase_time - c.click_time as click_to_purchase,
  c.purchase_time - pe.sent_at as publication_to_purchase
from offers.shopee_conversions c
join offers.publication_events pe on pe.dispatch_plan_id = c.dispatch_plan_id
where pe.sent_at is not null;
```

### 7.8 Cobertura de tracking

Meta: 100% das exposições Shopee publicadas com `tracking_status='ready'`, short URL não nula e quatro Sub IDs.

### 7.9 Raw clicks não atribuídos

```sql
select
  date(click_time at time zone 'America/Sao_Paulo') as click_date,
  count(*) as raw_clicks,
  count(*) filter (where dispatch_plan_id is not null) as attributed_clicks,
  count(*) filter (where dispatch_plan_id is null) as unattributed_clicks,
  count(*) filter (where sub_id_raw = '----') as legacy_empty_sub_id
from offers.shopee_click_events
group by 1
order by 1;
```

### 7.10 Reconciliação futura com `validatedReport`

Quando o fluxo de `validationId` estiver definido, comparar por `conversion_id` o `totalCommission` observado em `conversionReport` com o valor correspondente no relatório validado. Até lá, essa query/report não bloqueia a primeira entrega.

## 8. `product_type` editorial — evolução futura

O futuro `product_type` interno representa função comercial/editorial do produto, por exemplo `serum`, `hidratante`, `calcinha`, `sutia`.

Ele não existe hoje e não é requisito desta instrumentação. Sua origem futura permanece aberta, provavelmente ligada a descoberta/taxonomia, palavras-chave, título, subnicho e categorias.

O `productType` retornado pela Shopee é um campo externo e não deve ser automaticamente equiparado ao conceito editorial interno.

## 9. Critérios de aceite 1–10

1. existe uma operação única `refresh → planner → tracking`;
2. refresh e planner mantêm seus contratos funcionais atuais;
3. cada plano Shopee possui `dispatch_plan_id` antes do tracking;
4. `originUrl` vem de `catalog_items.product_link`;
5. Sub IDs seguem exatamente `wa`, `profile`, `dp<uuid_sem_hifens>`, `item_id`;
6. a short URL é persistida por exposição e não no catálogo global;
7. `v_daily_dispatch_ready.offer_link` entrega a short URL rastreável;
8. nenhuma exposição Shopee é publicada sem tracking válido;
9. Click Report CSV pode ser importado idempotentemente preservando a linha raw; `click_id` é indexado mas não assumido globalmente único;
10. a presença de múltiplos Sub IDs no relatório está suportada pela documentação oficial; o parser concreto depende apenas da confirmação de serialização/delimitador no CSV do teste.

## 10. Review de pendências

### 10.1 Pendências que bloqueiam apenas partes específicas

**P1 — serialização concreta dos Sub IDs no CSV.**

A existência dos Sub IDs no relatório está documentada. Falta apenas observar o CSV gerado pelo teste para definir delimitador/parser concreto. Isso bloqueia somente a implementação final do parser de raw clicks, não o schema nem o restante do pipeline.

**P2 — origem programática do `validationId`.**

O Playground/API observado exige `validationId` para `validatedReport`, mas o `conversionReport` real não o retorna. É necessário localizar, em fonte oficial/API disponível à conta, o fluxo que fornece esse identificador. Isso bloqueia apenas a reconciliação via `validatedReport`, não tracking, clicks ou analytics de `conversionReport`.

### 10.2 Detalhes de implementação ainda a fechar, mas sem decisão de negócio pendente

- constraints/checks SQL finais para `tracking_status` e cardinalidade dos Sub IDs;
- índices finais além de `click_id`, `dispatch_plan_id`, `conversion_id`, `order_id`;
- estratégia de retry/backoff da API;
- política de atualização/idempotência de conversões quando o mesmo `conversion_id` reaparece;
- período/cadência da sincronização de `conversionReport`;
- mecanismo operacional de upload/importação do Click Report inicialmente manual;
- testes de paginação com `scrollId` e seu comportamento real;
- view agregada canônica por `dispatch_plan_id` para reporting e prevenção de multiplicação em joins 1:N.

### 10.3 Decisões que NÃO estão mais pendentes

- KPI econômico principal: `totalCommission`;
- direta/indireta: comparação entre `daily_dispatch_plan.item_id` e item comprado `items.itemId`;
- `shop_id` do item anunciado não é necessário para essa classificação;
- Click Report é a fonte de todos os raw clicks e é obtido fora da Open API observada;
- múltiplos Sub IDs são suportados no relatório conforme documentação oficial;
- `ID dos Cliques` não recebe `UNIQUE` sem contrato explícito de unicidade global;
- `validatedReport` é reconciliação financeira posterior e não bloqueia a primeira implementação;
- `product_type` editorial permanece fora desta fase.

## 11. Fora de escopo

- mudança do `commercial_score`;
- redistribuição editorial baseada em cliques antes de acumular evidência;
- algoritmo do futuro `product_type`;
- mudança das regras internas de refresh/planner;
- redefinição da copy;
- automação do download do Click Report enquanto não houver mecanismo confirmado;
- inferências não suportadas sobre campos externos Shopee.

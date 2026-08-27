# Spec — Rastreamento de cliques, conversões e diversidade funcional na Shopee

Status: especificação funcional e técnica para instrumentação de rastreamento e base analítica. As regras comerciais/editoriais existentes permanecem preservadas. A modelagem de `product_type` editorial continua como evolução futura.

## 1. Escopo técnico e orquestração diária

### 1.1 Objetivo de negócio

O objetivo desta evolução não é copiar os relatórios da Shopee para o Supabase. O objetivo é responder, com evidência, às perguntas centrais da operação:

1. qual exposição/publicação merece ocupar espaço no grupo;
2. quais exposições geram interesse, medido por clique;
3. quais exposições geram monetização direta ou indireta;
4. qual item foi anunciado versus qual item foi efetivamente comprado;
5. quanto valor cada slot editorial produziu;
6. futuramente, se há saturação por tipo funcional de produto mesmo quando os `item_id` são diferentes.

A unidade canônica de análise é a **exposição planejada**, identificada por `daily_dispatch_plan.dispatch_plan_id`.

A instrumentação deve permitir analisar, por exposição:

```text
publicação
→ cliques
→ conversões
→ pedidos
→ itens comprados
→ comissão
```

sem substituir o `commercial_score` atual antes de existir evidência suficiente.

### 1.2 Decisão de orquestração

Hoje existem caminhos operacionais separados para:

- refresh de candidatos/ofertas Shopee;
- planejamento e persistência da fila diária em `offers.daily_dispatch_plan`.

Esta evolução deve consolidar a execução diária em **uma única orquestração sequencial**, composta por três estágios funcionais e uma liberação final:

```text
1. Refresh Shopee existente
   ↓
2. Planejamento da fila diária existente
   ↓
3. Geração das short URLs rastreáveis
   ↓
4. Liberação da fila para consumo/publicação
```

A terceira etapa só pode ocorrer depois da criação de `offers.daily_dispatch_plan`, porque o `dispatch_plan_id` é parte obrigatória do tracking.

A consolidação é de **orquestração**, e não uma fusão monolítica dos componentes. Refresh e planner devem continuar testáveis e executáveis isoladamente para diagnóstico.

### 1.3 O que deve ser alterado

Devem ser alterados somente os pontos necessários para:

- criar uma operação diária única que execute refresh, planner e geração de tracking em ordem;
- gerar uma short URL Shopee para cada exposição planejada;
- persistir o resultado por `dispatch_plan_id`;
- liberar para publicação somente exposições com tracking válido;
- fazer a superfície consumida pelo publicador entregar a nova short URL no campo `offer_link` já esperado pela copy;
- criar estruturas persistentes para ingestão do Click Report CSV;
- criar estruturas persistentes para `conversionReport` e `validatedReport`;
- permitir análises por exposição, clique, conversão e item comprado.

### 1.4 O que NÃO deve ser alterado

A consolidação **NÃO DEVE alterar o escopo funcional dos dois processos existentes**.

No refresh, não alterar por causa desta spec:

- critérios de candidatos;
- políticas e limites de refresh;
- regras `FRESH`/`STALE`;
- snapshots;
- critérios de estabilidade;
- lógica de scoring ou elegibilidade.

No planejamento diário, não alterar por causa desta spec:

- `commercial_score`;
- pesos de score;
- quotas;
- distribuição editorial;
- rotação;
- fallback;
- cooldown;
- subnichos/taxonomia;
- número de slots;
- horários e sequenciamento;
- critérios atuais de elegibilidade;
- regras atuais de gravação/substituição da `daily_dispatch_plan`.

No publicador/n8n, não alterar por causa desta spec:

- copy existente, exceto pelo fato de o mesmo campo `offer_link` passar a conter a URL rastreável da exposição;
- allowlist;
- destino/grupo WhatsApp;
- WAHA/conexão existente;
- regras atuais de claim, consumo e registro do envio;
- estrutura editorial da mensagem.

## 2. Fontes de dados e identidade já disponíveis

### 2.1 Supabase

Em `offers.daily_dispatch_plan` já existem, entre outros:

- `dispatch_plan_id UUID NOT NULL`;
- `profile TEXT NOT NULL`;
- `marketplace TEXT NOT NULL`;
- `stable_key TEXT NOT NULL`;
- `item_id BIGINT NOT NULL`;
- `primary_subniche TEXT NOT NULL`;
- `commercial_score NUMERIC NOT NULL`;
- `selection_bucket TEXT NOT NULL`;
- `selection_reason TEXT NOT NULL`;
- `planned_date DATE NOT NULL`;
- `planned_hour SMALLINT NOT NULL`;
- `slot_sequence SMALLINT NOT NULL`;
- `daily_sequence SMALLINT NOT NULL`;
- `publication_event_id UUID NULL`;
- `consumed_at TIMESTAMPTZ NULL`.

Em `offers.catalog_items` já existem, entre outros:

- `product_link`;
- `offer_link`;
- `item_id`;
- `profile`;
- `marketplace`;
- informações comerciais e editoriais do item.

Em `offers.publication_events` já existem, entre outros:

- `publish_id UUID NOT NULL`;
- `dispatch_plan_id UUID NULL`;
- `profile TEXT NOT NULL`;
- `marketplace TEXT NOT NULL`;
- `item_id BIGINT NULL`;
- `target TEXT NOT NULL`;
- `channel_adapter TEXT NOT NULL`;
- `delivery_status TEXT NOT NULL`;
- `planned_at TIMESTAMPTZ NULL`;
- `sent_at TIMESTAMPTZ NULL`;
- `offer_title TEXT NOT NULL`;
- `offer_url TEXT NOT NULL`;
- `offer_price NUMERIC NULL`;
- `message_text TEXT NOT NULL`.

O `dispatch_plan_id` é a chave canônica pré-publicação. O `publish_id` continua sendo a identidade do evento de publicação registrado após o envio.

### 2.2 Cadeia de identidade

```text
daily_dispatch_plan.dispatch_plan_id
  → Sub ID da exposição
  → short URL específica da exposição
  → publication_events.publish_id
  → Click Report CSV
  → conversionReport / validatedReport
```

Informações já conhecidas pela exposição — `profile`, `item_id`, `primary_subniche`, `commercial_score`, horário e slot — **não devem ser duplicadas desnecessariamente** nas tabelas de clique/conversão. Elas devem ser recuperadas por `dispatch_plan_id`.

## 3. Fontes externas Shopee

### 3.1 Click Report — fonte de raw clicks

O Click Report **não está disponível na Open API observada**. Ele precisa ser baixado pela Central/Central de Comando da Shopee e posteriormente ingerido pelo projeto.

O CSV fornecido anteriormente possui exatamente as colunas:

- `ID dos Cliques`;
- `Tempo dos Cliques`;
- `Região dos Cliques`;
- `Sub_id`;
- `Referenciador`.

O arquivo analisado continha 48 raw clicks e todos possuíam `Sub_id = ----`. Portanto esses cliques históricos continuam úteis como volume bruto, mas não podem ser reconciliados deterministicamente com uma exposição específica.

O Click Report é a fonte primária para **interesse/tráfego**, porque inclui cliques sem compra.

O campo `Referenciador` não deve ser usado como chave principal de atribuição.

### 3.2 Gap ainda aberto: serialização de múltiplos `subIds` no Click Report

Foi gerada e testada a short URL:

```text
https://s.shopee.com.br/3g3DPzjYgO
```

com os quatro Sub IDs:

```text
[
  "wa",
  "feminino",
  "dp550e8400e29b41d4a716446655440000",
  "18797641257"
]
```

O teste de `generateShortLink` confirma que a API aceita os quatro valores e retorna a short URL.

**Ainda falta confirmar empiricamente como esses quatro valores aparecem na única coluna `Sub_id` do Click Report CSV.**

O teste planejado consiste em gerar múltiplos cliques nessa short URL e baixar um novo Click Report no dia seguinte.

Até observar esse arquivo:

- não fixar delimitador;
- não fixar parser;
- não assumir que os quatro valores aparecem separadamente;
- preservar sempre o `Sub_id` bruto recebido.

### 3.3 `conversionReport`

Query de referência fornecida:

```graphql
{
  conversionReport(
    conversionStatus: ALL,
    productId: 22599034226,
    categoryType: ALL,
    orderStatus: ALL,
    buyerType: ALL,
    productType: ALL,
    fraudStatus: ALL,
    device: ALL
  ) {
    nodes {
      clickTime
      purchaseTime
      conversionId
      shopeeCommissionCapped
      sellerCommission
      totalCommission
      netCommission
      mcnManagementFeeRate
      mcnManagementFee
      mcnContractId
      linkedMcnName
      buyerType
      utmContent
      device
      productType
      referrer
      orders {
        orderId
        shopType
        orderStatus
        items {
          shopId
          shopName
          completeTime
          promotionId
          modelId
          itemId
          itemName
          itemPrice
          displayItemStatus
          actualAmount
          refundAmount
          qty
          imageUrl
          itemTotalCommission
          itemSellerCommission
          itemSellerCommissionRate
          itemShopeeCommissionCapped
          itemShopeeCommissionRate
          itemNotes
          globalCategoryLv1Name
          globalCategoryLv2Name
          globalCategoryLv3Name
          fraudStatus
          fraudReason
          attributionType
          channelType
          campaignPartnerName
          campaignType
        }
      }
    }
    pageInfo {
      page
      limit
      hasNextPage
      scrollId
    }
  }
}
```

O `productId: 22599034226` desse exemplo é **fictício para teste** e não deve ser tratado como constante ou dado real do projeto.

A query observada demonstra filtros para:

- `conversionStatus`;
- `productId`;
- `categoryType`;
- `orderStatus`;
- `buyerType`;
- `productType`;
- `fraudStatus`;
- `device`.

Não inferir a obrigatoriedade ou opcionalidade desses argumentos apenas a partir do exemplo.

O `clickTime` desse relatório representa o clique associado à conversão e **não substitui o Click Report para o universo de raw clicks**.

### 3.4 `validatedReport`

Query de referência fornecida:

```graphql
{
  validatedReport {
    nodes {
      clickTime
      purchaseTime
      conversionId
      shopeeCommissionCapped
      sellerCommission
      totalCommission
      buyerType
      utmContent
      device
      productType
      referrer
      netCommission
      mcnManagementFeeRate
      mcnManagementFee
      mcnContractId
      linkedMcnName
      orders {
        orderId
        shopType
        orderStatus
        items {
          shopId
          shopName
          completeTime
          promotionId
          modelId
          itemId
          itemName
          itemPrice
          displayItemStatus
          actualAmount
          refundAmount
          qty
          imageUrl
          itemTotalCommission
          itemSellerCommission
          itemSellerCommissionRate
          itemShopeeCommissionCapped
          itemShopeeCommissionRate
          itemNotes
          globalCategoryLv1Name
          globalCategoryLv2Name
          globalCategoryLv3Name
          fraudStatus
          fraudReason
          attributionType
          channelType
          campaignPartnerName
          campaignType
        }
      }
    }
    pageInfo {
      page
      limit
      hasNextPage
      scrollId
    }
  }
}
```

No exemplo fornecido, `validatedReport` foi chamado sem argumentos. Isso não autoriza inferir que outros formatos/filtros não existam.

A diferença semântica exata entre `conversionReport` e `validatedReport` permanece aberta. **Não sobrescrever silenciosamente um pelo outro.** Preservar a origem da observação.

## 4. Contrato obrigatório de tracking e short URL

### 4.1 Momento de geração

A linha pode ser criada em `offers.daily_dispatch_plan` antes da URL rastreável, pois o próprio `dispatch_plan_id` participa da chamada.

Porém, uma linha Shopee **não pode ser exposta como pronta para publicação** até a geração e persistência bem-sucedida da short URL rastreável.

```text
PLANNED
  daily_dispatch_plan existe
  dispatch_plan_id existe
      ↓
TRACKING
  generateShortLink executado
  shortLink persistida
      ↓
READY
  v_daily_dispatch_ready expõe a linha
```

Não deve existir fallback silencioso para publicação usando URL não rastreada.

### 4.2 URL de entrada e URL consumida pela copy

Entrada da API:

```text
offers.catalog_items.product_link
```

Fluxo:

```text
catalog_items.product_link
        ↓ originUrl
generateShortLink
        ↓ shortLink
tracking_short_url da exposição planejada
        ↓ exposta como offer_link
v_daily_dispatch_ready
        ↓
n8n / copy / WhatsApp
```

O n8n atual consome `offer_link` na copy e esse contrato deve ser preservado.

**Não sobrescrever globalmente `catalog_items.offer_link` com uma URL específica de `dispatch_plan_id`.** A short URL pertence à exposição planejada. O mesmo produto reutilizado em outro plano deve receber outra short URL.

### 4.3 Quatro Sub IDs obrigatórios

| Posição | Conteúdo | Regra | Exemplo |
| --- | --- | --- | --- |
| `subId[0]` | meio | literal deste fluxo | `wa` |
| `subId[1]` | perfil | `daily_dispatch_plan.profile` sem mapping manual | `feminino` |
| `subId[2]` | exposição | `dp` + UUID sem hífens | `dp550e8400e29b41d4a716446655440000` |
| `subId[3]` | item anunciado | `item_id` como texto | `18797641257` |

A quinta posição permanece reservada.

O uso direto de `profile` evita tabelas manuais de abreviação e torna novos profiles automaticamente rastreáveis.

### 4.4 Normalização de `dispatch_plan_id`

```text
550e8400-e29b-41d4-a716-446655440000
        ↓ remover '-'
550e8400e29b41d4a716446655440000
        ↓ prefixar 'dp'
dp550e8400e29b41d4a716446655440000
```

Regra:

```text
dispatch_tracking_id = "dp" + replace(dispatch_plan_id::text, "-", "")
```

Não usar underscore, hífen, truncamento ou hash.

Esse formato completo foi validado em chamada real de `generateShortLink`.

### 4.5 Exemplo validado

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

Retorno observado de `shortLink`:

```text
https://s.shopee.com.br/3g3DPzjYgO
```

### 4.6 Precondições para READY

Uma exposição Shopee somente pode ficar `READY` quando:

- existir `product_link` válida;
- `profile` estiver presente;
- `dispatch_plan_id` estiver presente;
- `item_id` estiver presente;
- os quatro Sub IDs forem produzidos conforme contrato;
- `generateShortLink` retornar uma `shortLink` válida;
- a short URL tiver sido persistida para aquele `dispatch_plan_id`.

Falha de tracking bloqueia somente a exposição afetada e não autoriza envio sem rastreamento.

## 5. Princípio de modelagem do banco

O banco deve ser modelado pelas **decisões de negócio**, não pela quantidade de campos que a Shopee fornece.

Princípios:

1. `dispatch_plan_id` é a chave da exposição;
2. não duplicar na conversão/clique dados já recuperáveis do plano;
3. preservar raw/origem externa suficiente para auditoria e reprocessamento;
4. criar colunas explícitas para dados usados nas análises principais;
5. manter `raw_payload JSONB` para campos externos secundários e evolução futura;
6. separar item anunciado de item comprado;
7. preservar a origem `conversion_report` versus `validated_report`;
8. não transformar o Supabase em réplica integral do schema externo.

## 6. Esquema proposto das tabelas

### 6.1 Alteração de `offers.daily_dispatch_plan` — tracking da exposição

**Fonte:** processo interno + retorno de `generateShortLink`.

| Coluna | Tipo sugerido | Origem | Uso |
| --- | --- | --- | --- |
| `tracking_sub_ids` | `TEXT[] NULL` | request `generateShortLink` | auditoria dos 4 Sub IDs enviados |
| `tracking_short_url` | `TEXT NULL` | `generateShortLink.shortLink` | URL efetiva da publicação |
| `tracking_generated_at` | `TIMESTAMPTZ NULL` | interno | auditoria |
| `tracking_status` | `TEXT NOT NULL DEFAULT 'pending'` | interno | `pending/ready/failed` |
| `tracking_error` | `TEXT NULL` | interno | diagnóstico técnico |

Regras:

- `tracking_sub_ids` deve ter exatamente quatro posições quando `tracking_status='ready'`;
- `tracking_short_url` deve existir quando `tracking_status='ready'`;
- `catalog_items.product_link` permanece inalterado;
- `catalog_items.offer_link` não é sobrescrito pela short URL de uma exposição;
- `v_daily_dispatch_ready.offer_link` deve projetar `daily_dispatch_plan.tracking_short_url` para Shopee.

### 6.2 `offers.shopee_click_report_imports` — lotes do CSV

**Fonte:** arquivo baixado manualmente da Central Shopee.

Finalidade: idempotência e proveniência do arquivo.

| Coluna | Tipo sugerido | Origem |
| --- | --- | --- |
| `import_id` | `UUID PK` | interno |
| `source_filename` | `TEXT NOT NULL` | arquivo |
| `source_sha256` | `TEXT NOT NULL UNIQUE` | hash do arquivo |
| `downloaded_at` | `TIMESTAMPTZ NULL` | informado/operacional |
| `imported_at` | `TIMESTAMPTZ NOT NULL` | interno |
| `row_count` | `INTEGER NOT NULL` | ingestão |
| `status` | `TEXT NOT NULL` | interno |
| `error` | `TEXT NULL` | interno |
| `created_at` | `TIMESTAMPTZ NOT NULL` | interno |

### 6.3 `offers.shopee_click_events` — raw clicks + resolução

**Fonte:** uma linha do Click Report CSV.

A mesma tabela preserva o raw e os campos resolvidos; não é necessário criar uma terceira tabela analítica apenas para repetir o clique.

| Coluna | Tipo sugerido | Origem | Importância |
| --- | --- | --- | --- |
| `click_event_id` | `UUID PK` | interno | chave técnica |
| `import_id` | `UUID NOT NULL FK` | lote | proveniência |
| `click_id` | `TEXT NOT NULL` | `ID dos Cliques` | identidade externa do evento |
| `click_time` | `TIMESTAMPTZ NOT NULL` | `Tempo dos Cliques` | análise temporal |
| `click_region` | `TEXT NULL` | `Região dos Cliques` | dado secundário preservado |
| `sub_id_raw` | `TEXT NULL` | `Sub_id` | raw obrigatório |
| `referrer` | `TEXT NULL` | `Referenciador` | auditoria/origem secundária |
| `dispatch_plan_id` | `UUID NULL FK` | derivado de `sub_id_raw` | ligação principal quando resolvida |
| `advertised_item_id_raw` | `BIGINT NULL` | derivado do tracking | validação contra plano |
| `tracking_parse_status` | `TEXT NOT NULL` | interno | `unparsed/resolved/unrecognized/legacy_empty` |
| `tracking_parse_error` | `TEXT NULL` | interno | diagnóstico |
| `raw_row` | `JSONB NOT NULL` | CSV original | reprocessamento/auditoria |
| `created_at` | `TIMESTAMPTZ NOT NULL` | interno | auditoria |

Observações:

- `profile`, `primary_subniche`, `commercial_score` e slot **não precisam ser duplicados**: vêm do `dispatch_plan_id`;
- `sub_id_raw='----'` deve ser preservado e classificado como legado/não atribuível;
- a estratégia final de parsing fica pendente do CSV gerado após o teste dos quatro Sub IDs;
- `click_id` não deve ser assumido como usuário único;
- após confirmar unicidade, pode ser criada constraint de idempotência apropriada sobre `click_id`; até lá, `source_sha256 + linha/raw` deve permitir reprocessamento seguro.

### 6.4 `offers.shopee_conversion_sync_runs` — execuções da API

**Fonte:** cada execução de `conversionReport` ou `validatedReport`.

| Coluna | Tipo sugerido | Origem |
| --- | --- | --- |
| `sync_run_id` | `UUID PK` | interno |
| `report_type` | `TEXT NOT NULL` | `conversion_report` / `validated_report` |
| `query_filters` | `JSONB NOT NULL` | filtros efetivamente usados |
| `started_at` | `TIMESTAMPTZ NOT NULL` | interno |
| `finished_at` | `TIMESTAMPTZ NULL` | interno |
| `status` | `TEXT NOT NULL` | interno |
| `nodes_received` | `INTEGER NOT NULL DEFAULT 0` | ingestão |
| `last_page` | `INTEGER NULL` | `pageInfo.page` |
| `page_limit` | `INTEGER NULL` | `pageInfo.limit` |
| `has_next_page` | `BOOLEAN NULL` | `pageInfo.hasNextPage` |
| `last_scroll_id` | `TEXT NULL` | `pageInfo.scrollId` |
| `error` | `TEXT NULL` | interno |
| `created_at` | `TIMESTAMPTZ NOT NULL` | interno |

`query_filters` deve preservar inclusive `productId` quando usado. O `productId` fictício do exemplo não deve ser persistido como default da aplicação.

### 6.5 `offers.shopee_conversions` — conversão canônica

**Fonte:** campos de nível `nodes` de `conversionReport`/`validatedReport`.

A tabela canônica contém apenas dados necessários para atribuição temporal e econômica. Campos externos secundários permanecem nas observações/raw payload.

| Coluna | Tipo sugerido | Origem | Uso |
| --- | --- | --- | --- |
| `conversion_id` | `TEXT PK` | `conversionId` | identidade natural |
| `dispatch_plan_id` | `UUID NULL FK` | resolvido de `utmContent` | ligação à exposição |
| `utm_content_raw` | `TEXT NULL` | `utmContent` | preservação da atribuição externa |
| `click_time` | `TIMESTAMPTZ NULL` | `clickTime` | latência publicação→clique convertido |
| `purchase_time` | `TIMESTAMPTZ NULL` | `purchaseTime` | latência clique→compra |
| `buyer_type` | `TEXT NULL` | `buyerType` | segmentação futura |
| `total_commission` | `NUMERIC NULL` | `totalCommission` | monetização bruta observada |
| `net_commission` | `NUMERIC NULL` | `netCommission` | monetização líquida observada |
| `seller_commission` | `NUMERIC NULL` | `sellerCommission` | composição da comissão |
| `shopee_commission_capped` | `NUMERIC NULL` | `shopeeCommissionCapped` | composição da comissão |
| `first_seen_at` | `TIMESTAMPTZ NOT NULL` | interno | auditoria |
| `last_seen_at` | `TIMESTAMPTZ NOT NULL` | interno | auditoria |
| `created_at` | `TIMESTAMPTZ NOT NULL` | interno | auditoria |
| `updated_at` | `TIMESTAMPTZ NOT NULL` | interno | auditoria |

Não é necessário duplicar aqui `profile`, `subniche`, `commercial_score`, `item_id` anunciado ou horário do slot.

### 6.6 `offers.shopee_conversion_observations` — estado visto em cada relatório

**Fonte:** um node observado por um `sync_run`.

Finalidade: evitar que `validatedReport` sobrescreva silenciosamente `conversionReport` antes de conhecermos sua semântica exata.

| Coluna | Tipo sugerido | Origem |
| --- | --- | --- |
| `observation_id` | `UUID PK` | interno |
| `conversion_id` | `TEXT NOT NULL FK` | `conversionId` |
| `sync_run_id` | `UUID NOT NULL FK` | execução |
| `report_type` | `TEXT NOT NULL` | origem |
| `observed_at` | `TIMESTAMPTZ NOT NULL` | interno |
| `total_commission` | `NUMERIC NULL` | API |
| `net_commission` | `NUMERIC NULL` | API |
| `seller_commission` | `NUMERIC NULL` | API |
| `shopee_commission_capped` | `NUMERIC NULL` | API |
| `mcn_management_fee_rate` | `NUMERIC NULL` | API |
| `mcn_management_fee` | `NUMERIC NULL` | API |
| `mcn_contract_id` | `TEXT NULL` | API |
| `linked_mcn_name` | `TEXT NULL` | API |
| `device` | `TEXT NULL` | API |
| `shopee_product_type` | `TEXT NULL` | API `productType` |
| `referrer` | `TEXT NULL` | API |
| `raw_payload` | `JSONB NOT NULL` | node original |

O `productType` externo da Shopee **não é o mesmo conceito** que o futuro `product_type` editorial do projeto.

### 6.7 `offers.shopee_conversion_orders` — pedidos

**Fonte:** `nodes[].orders[]`.

| Coluna | Tipo sugerido | Origem |
| --- | --- | --- |
| `conversion_order_id` | `UUID PK` | interno |
| `conversion_id` | `TEXT NOT NULL FK` | parent node |
| `order_id` | `TEXT NOT NULL` | `orderId` |
| `shop_type` | `TEXT NULL` | `shopType` |
| `order_status` | `TEXT NULL` | `orderStatus` |
| `first_seen_at` | `TIMESTAMPTZ NOT NULL` | interno |
| `last_seen_at` | `TIMESTAMPTZ NOT NULL` | interno |
| `raw_payload` | `JSONB NULL` | pedido original |

Chave natural proposta para estado corrente: `conversion_id + order_id`.

### 6.8 `offers.shopee_conversion_items` — itens efetivamente comprados

**Fonte:** `nodes[].orders[].items[]`.

Essa tabela é central para distinguir o produto anunciado do produto comprado.

#### Colunas analíticas de primeira classe

| Coluna | Tipo sugerido | Origem | Uso |
| --- | --- | --- | --- |
| `conversion_item_id` | `UUID PK` | interno | chave técnica |
| `conversion_id` | `TEXT NOT NULL FK` | node | ligação à conversão |
| `order_id` | `TEXT NOT NULL` | pedido | ligação ao pedido |
| `item_id` | `BIGINT NOT NULL` | `itemId` | item comprado |
| `shop_id` | `BIGINT NULL` | `shopId` | mesma loja/outra loja |
| `item_name` | `TEXT NULL` | `itemName` | leitura/auditoria |
| `item_price` | `NUMERIC NULL` | `itemPrice` | valor de referência |
| `actual_amount` | `NUMERIC NULL` | `actualAmount` | valor efetivo |
| `refund_amount` | `NUMERIC NULL` | `refundAmount` | ajuste econômico |
| `qty` | `INTEGER NULL` | `qty` | quantidade |
| `item_total_commission` | `NUMERIC NULL` | `itemTotalCommission` | valor gerado pelo item |
| `global_category_lv1_name` | `TEXT NULL` | API | demanda comprada |
| `global_category_lv2_name` | `TEXT NULL` | API | demanda comprada |
| `global_category_lv3_name` | `TEXT NULL` | API | demanda comprada |
| `fraud_status` | `TEXT NULL` | API | integridade |
| `attribution_type` | `TEXT NULL` | API | atribuição externa sem inferência |
| `complete_time` | `TIMESTAMPTZ NULL` | `completeTime` | ciclo do pedido |
| `raw_payload` | `JSONB NOT NULL` | item original | auditoria/evolução |

#### Campos preservados no `raw_payload` e não obrigatoriamente promovidos a coluna nesta fase

- `shopName`;
- `promotionId`;
- `modelId`;
- `displayItemStatus`;
- `imageUrl`;
- `itemSellerCommission`;
- `itemSellerCommissionRate`;
- `itemShopeeCommissionCapped`;
- `itemShopeeCommissionRate`;
- `itemNotes`;
- `fraudReason`;
- `channelType`;
- `campaignPartnerName`;
- `campaignType`.

Esses campos não são descartados; apenas não dirigem o desenho analítico inicial.

### 6.9 Diagrama lógico

```text
offers.daily_dispatch_plan
  PK dispatch_plan_id
  item_id anunciado
  primary_subniche
  commercial_score
  tracking_short_url
  tracking_sub_ids
          │
          ├─────────────── 0..1 offers.publication_events
          │
          ├─────────────── 0..N offers.shopee_click_events
          │                         raw CSV + dispatch_plan_id resolvido
          │
          └─────────────── 0..N offers.shopee_conversions
                                    │
                                    ├── 0..N sho...conversion_observations
                                    └── 1..N sho...conversion_orders
                                                   │
                                                   └── 1..N sho...conversion_items
                                                          item_id comprado
```

Tabelas operacionais auxiliares:

```text
shopee_click_report_imports → controla arquivos CSV
shopee_conversion_sync_runs → controla chamadas/paginação da API
```

## 7. Classificação de valor da exposição

A arquitetura deve permitir, sem inventar semântica da Shopee, comparar:

```text
item anunciado = daily_dispatch_plan.item_id
item comprado  = shopee_conversion_items.item_id
```

e, quando a loja do item anunciado estiver disponível de forma confiável no catálogo/snapshot:

```text
1. mesmo item anunciado
2. outro item da mesma loja
3. outro item/outra loja
```

`attribution_type` deve ser armazenado como evidência externa e só interpretado após observar valores reais/documentação oficial.

O objetivo analítico é medir o **valor do slot editorial**, não apenas “o item anunciado vendeu ou não”.

## 8. `product_type` editorial — evolução futura

O futuro `product_type` editorial representa função comercial do produto dentro do subnicho, por exemplo:

```text
skincare-facial → serum
skincare-facial → hidratante
lingerie-e-intimos → calcinha
lingerie-e-intimos → sutia
```

Esse campo não existe hoje no Supabase e não é requisito desta implementação.

Origem futura permanece aberta, provavelmente relacionada a descoberta/taxonomia por palavras-chave, título, subnicho e categorias.

O `productType` retornado pela Shopee no relatório de conversão é um dado externo e **não deve ser automaticamente equiparado** ao futuro `product_type` editorial.

## 9. Entradas e saídas formais

### 9.1 Preparação diária

Entradas da terceira etapa:

- `dispatch_plan_id`;
- `profile`;
- `item_id`;
- `marketplace`;
- `catalog_items.product_link`.

Saída persistida:

```text
dispatch_plan_id
tracking_sub_ids[4]
tracking_short_url
tracking_generated_at
tracking_status
```

Saída para o publicador:

```text
offer_link = tracking_short_url
```

### 9.2 Click Report

Entrada:

```text
CSV baixado manualmente da Central Shopee
```

Saída:

```text
import lot
+ raw click events
+ dispatch_plan_id resolvido quando possível
```

### 9.3 Relatórios de conversão

Entrada:

```text
conversionReport / validatedReport paginados
```

Saída:

```text
sync_run
+ conversion canonical
+ observation por relatório
+ orders
+ purchased items
```

## 10. Métricas principais

### 10.1 Exposição

- publicações por subnicho;
- publicações por `item_id`;
- distribuição por horário/slot;
- concentração de exposição.

### 10.2 Interesse

- raw clicks totais;
- cliques atribuídos por exposição;
- cliques por publicação;
- cliques por item anunciado;
- cliques por subnicho via join;
- latência publicação → primeiro clique;
- percentual de clicks não atribuídos.

Enquanto não houver impressões confiáveis do WhatsApp, usar `cliques por publicação`, não denominar CTR.

### 10.3 Monetização

- conversões por exposição;
- comissão total e líquida por exposição;
- comissão por clique;
- item anunciado versus item comprado;
- categorias compradas;
- latência clique convertido → compra;
- diferença entre estado observado em `conversionReport` e `validatedReport`.

### 10.4 Integridade

- 100% das novas exposições Shopee publicadas com tracking válido;
- 100% com short URL persistida;
- Click Report com `Sub_id` não reconhecido;
- `utmContent` não reconhecido;
- divergência entre item anunciado no tracking e plano;
- publicação sem plano;
- conversão sem plano resolvido;
- duplicidade indevida de identidade.

## 11. Queries analíticas propostas

As queries abaixo são **propostas de leitura** sobre o schema desta spec. Nomes finais podem ser ajustados na migração, mas as perguntas de negócio são parte do contrato.

### 11.1 Valor por exposição

Pergunta: **quais publicações geraram mais interesse e dinheiro por slot?**

```sql
with clicks as (
  select
    dispatch_plan_id,
    count(*) as clicks,
    min(click_time) as first_click_at
  from offers.shopee_click_events
  where dispatch_plan_id is not null
  group by dispatch_plan_id
), conversions as (
  select
    dispatch_plan_id,
    count(*) as conversions,
    sum(coalesce(total_commission, 0)) as total_commission,
    sum(coalesce(net_commission, 0)) as net_commission
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
  coalesce(c.clicks, 0) as clicks,
  coalesce(v.conversions, 0) as conversions,
  coalesce(v.total_commission, 0) as total_commission,
  coalesce(v.net_commission, 0) as net_commission,
  case when coalesce(c.clicks, 0) > 0
       then v.net_commission / c.clicks
       else null end as net_commission_per_click,
  c.first_click_at - pe.sent_at as time_to_first_click
from offers.daily_dispatch_plan p
left join offers.publication_events pe
  on pe.dispatch_plan_id = p.dispatch_plan_id
left join clicks c
  on c.dispatch_plan_id = p.dispatch_plan_id
left join conversions v
  on v.dispatch_plan_id = p.dispatch_plan_id
where p.marketplace = 'shopee';
```

### 11.2 Performance por subnicho

Pergunta: **qual subnicho consome slots e qual retorno produz?**

```sql
with exposure_value as (
  -- substituir pela view/query 11.1
  select
    p.dispatch_plan_id,
    p.primary_subniche,
    count(distinct ce.click_event_id) as clicks,
    count(distinct c.conversion_id) as conversions,
    coalesce(sum(distinct c.net_commission), 0) as net_commission
  from offers.daily_dispatch_plan p
  left join offers.shopee_click_events ce
    on ce.dispatch_plan_id = p.dispatch_plan_id
  left join offers.shopee_conversions c
    on c.dispatch_plan_id = p.dispatch_plan_id
  where p.marketplace = 'shopee'
  group by p.dispatch_plan_id, p.primary_subniche
)
select
  primary_subniche,
  count(*) as exposures,
  sum(clicks) as clicks,
  sum(conversions) as conversions,
  sum(net_commission) as net_commission,
  sum(clicks)::numeric / nullif(count(*), 0) as clicks_per_exposure,
  sum(net_commission) / nullif(count(*), 0) as commission_per_exposure
from exposure_value
group by primary_subniche
order by commission_per_exposure desc nulls last;
```

Nota de implementação: evitar multiplicação de comissão por joins 1:N; preferir views/agregações intermediárias por `dispatch_plan_id`.

### 11.3 Item anunciado versus item comprado

Pergunta: **o produto converte diretamente ou funciona como gerador de tráfego para outras compras?**

```sql
select
  c.dispatch_plan_id,
  p.item_id as advertised_item_id,
  i.item_id as purchased_item_id,
  case
    when i.item_id = p.item_id then 'same_item'
    else 'different_item'
  end as purchase_relation,
  i.global_category_lv1_name,
  i.global_category_lv2_name,
  i.global_category_lv3_name,
  i.attribution_type,
  i.actual_amount,
  i.item_total_commission
from offers.shopee_conversions c
join offers.daily_dispatch_plan p
  on p.dispatch_plan_id = c.dispatch_plan_id
join offers.shopee_conversion_items i
  on i.conversion_id = c.conversion_id;
```

Quando houver `shop_id` confiável do item anunciado, evoluir o `case` para:

```text
same_item
same_shop_other_item
other_shop_item
```

### 11.4 Produtos anunciados que geram mais compra indireta

Pergunta: **quais produtos são bons geradores de jornada mesmo quando não são o item comprado?**

```sql
select
  p.item_id as advertised_item_id,
  count(distinct p.dispatch_plan_id) as exposures,
  count(distinct c.conversion_id) as conversions,
  count(*) filter (where i.item_id <> p.item_id) as different_item_lines,
  sum(i.item_total_commission) filter (where i.item_id <> p.item_id)
    as indirect_item_commission
from offers.daily_dispatch_plan p
join offers.shopee_conversions c
  on c.dispatch_plan_id = p.dispatch_plan_id
join offers.shopee_conversion_items i
  on i.conversion_id = c.conversion_id
group by p.item_id
order by indirect_item_commission desc nulls last;
```

A expressão “indireta” aqui é operacional (`item comprado != item anunciado`). Não substitui a semântica oficial de `attributionType`.

### 11.5 Categorias efetivamente compradas após nossas exposições

Pergunta: **o que a audiência realmente compra depois de entrar pela publicação?**

```sql
select
  i.global_category_lv1_name,
  i.global_category_lv2_name,
  i.global_category_lv3_name,
  count(*) as purchased_item_lines,
  sum(coalesce(i.qty, 0)) as units,
  sum(coalesce(i.actual_amount, 0)) as actual_amount,
  sum(coalesce(i.item_total_commission, 0)) as item_commission
from offers.shopee_conversion_items i
join offers.shopee_conversions c
  on c.conversion_id = i.conversion_id
where c.dispatch_plan_id is not null
group by
  i.global_category_lv1_name,
  i.global_category_lv2_name,
  i.global_category_lv3_name
order by item_commission desc nulls last;
```

### 11.6 Funil publicação → clique → conversão

Pergunta: **onde perdemos valor: exposição sem clique ou clique sem conversão?**

```sql
with clicks as (
  select dispatch_plan_id, count(*) as clicks
  from offers.shopee_click_events
  where dispatch_plan_id is not null
  group by dispatch_plan_id
), conv as (
  select dispatch_plan_id, count(*) as conversions
  from offers.shopee_conversions
  where dispatch_plan_id is not null
  group by dispatch_plan_id
)
select
  p.planned_date,
  count(*) as planned_exposures,
  count(pe.publish_id) filter (where pe.delivery_status = 'confirmed') as published,
  sum(coalesce(cl.clicks, 0)) as clicks,
  sum(coalesce(cv.conversions, 0)) as conversions,
  sum(coalesce(cl.clicks, 0))::numeric /
    nullif(count(pe.publish_id) filter (where pe.delivery_status = 'confirmed'), 0)
    as clicks_per_publication,
  sum(coalesce(cv.conversions, 0))::numeric /
    nullif(sum(coalesce(cl.clicks, 0)), 0)
    as conversions_per_click
from offers.daily_dispatch_plan p
left join offers.publication_events pe
  on pe.dispatch_plan_id = p.dispatch_plan_id
left join clicks cl
  on cl.dispatch_plan_id = p.dispatch_plan_id
left join conv cv
  on cv.dispatch_plan_id = p.dispatch_plan_id
where p.marketplace = 'shopee'
group by p.planned_date
order by p.planned_date;
```

`clicks_per_publication` não deve ser chamado de CTR enquanto não houver impressão individual confiável.

### 11.7 Latência publicação → clique → compra

Pergunta: **quanto tempo uma publicação leva para produzir ação econômica?**

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
join offers.publication_events pe
  on pe.dispatch_plan_id = c.dispatch_plan_id
where pe.sent_at is not null;
```

### 11.8 Cobertura e integridade do tracking

Pergunta: **a instrumentação está funcionando antes de confiar nas análises?**

```sql
select
  planned_date,
  count(*) as shopee_plans,
  count(*) filter (
    where tracking_status = 'ready'
      and tracking_short_url is not null
      and cardinality(tracking_sub_ids) = 4
  ) as tracked_ready,
  count(*) filter (where tracking_status = 'failed') as tracking_failed,
  round(
    100.0 * count(*) filter (
      where tracking_status = 'ready'
        and tracking_short_url is not null
        and cardinality(tracking_sub_ids) = 4
    ) / nullif(count(*), 0),
    2
  ) as tracking_coverage_pct
from offers.daily_dispatch_plan
where marketplace = 'shopee'
group by planned_date
order by planned_date;
```

### 11.9 Raw clicks não atribuídos

Pergunta: **quanto do interesse ainda não conseguimos ligar a uma exposição?**

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

### 11.10 Comparação `conversionReport` versus `validatedReport`

Pergunta: **o que mudou entre as observações dos dois relatórios?**

```sql
select
  o.conversion_id,
  max(o.total_commission) filter (where o.report_type = 'conversion_report')
    as conversion_report_commission,
  max(o.total_commission) filter (where o.report_type = 'validated_report')
    as validated_report_commission,
  max(o.net_commission) filter (where o.report_type = 'conversion_report')
    as conversion_report_net,
  max(o.net_commission) filter (where o.report_type = 'validated_report')
    as validated_report_net
from offers.shopee_conversion_observations o
group by o.conversion_id
order by o.conversion_id;
```

Essa query mostra diferenças observadas; **não interpreta por que existem** até a semântica do `validatedReport` ser formalmente confirmada.

### 11.11 Relação entre `commercial_score` e resultado observado

Pergunta: **o score atual está correlacionado com interesse/comissão real?**

```sql
with per_exposure as (
  select
    p.dispatch_plan_id,
    p.commercial_score,
    count(distinct ce.click_event_id) as clicks,
    coalesce(max(c.net_commission), 0) as net_commission
  from offers.daily_dispatch_plan p
  left join offers.shopee_click_events ce
    on ce.dispatch_plan_id = p.dispatch_plan_id
  left join offers.shopee_conversions c
    on c.dispatch_plan_id = p.dispatch_plan_id
  where p.marketplace = 'shopee'
  group by p.dispatch_plan_id, p.commercial_score
)
select
  width_bucket(commercial_score, 0, 100, 10) as score_bucket,
  count(*) as exposures,
  avg(clicks) as avg_clicks,
  avg(net_commission) as avg_net_commission
from per_exposure
group by score_bucket
order by score_bucket;
```

Os limites de score acima são exemplo de leitura e devem ser ajustados à escala real do `commercial_score` se não for 0–100.

## 12. Relatórios analíticos recomendados

A primeira camada de reporting deve ser pequena e orientada a decisão:

1. **Valor por exposição** — slots, cliques, conversões, comissão e latência;
2. **Performance por subnicho** — exposição versus interesse versus monetização;
3. **Item anunciado × item comprado** — mesma compra versus compra diferente;
4. **Demanda comprada** — categorias/itens efetivamente adquiridos;
5. **Funil diário** — publicações → raw clicks → conversões;
6. **Integridade do tracking** — cobertura, erros e não atribuídos;
7. **Score versus resultado observado** — evidência para futura evolução do ranking.

Futuramente, após criação do `product_type` editorial, adicionar:

- exposição por tipo funcional;
- clicks por tipo;
- comissão por tipo;
- concentração Top 1/Top 3/Top 5;
- valor marginal por slot funcional.

## 13. Critérios de aceite

A fase de instrumentação/modelagem é considerada tecnicamente pronta quando:

1. existe uma operação única refresh → planner → tracking;
2. refresh e planner mantêm seus contratos funcionais atuais;
3. cada plano Shopee possui `dispatch_plan_id` antes de gerar tracking;
4. `originUrl` vem de `catalog_items.product_link`;
5. Sub IDs seguem exatamente `wa`, `profile`, `dp<uuid_sem_hifens>`, `item_id`;
6. a short URL é persistida por exposição e não no catálogo global;
7. `v_daily_dispatch_ready.offer_link` entrega a short URL rastreável;
8. nenhuma exposição Shopee é publicada sem tracking válido;
9. o Click Report CSV pode ser importado idempotentemente e preserva a linha raw;
10. o parser de `Sub_id` só será fechado após observar o CSV do teste dos quatro Sub IDs;
11. `conversionReport` e `validatedReport` têm proveniência separada;
12. conversão, pedido e item comprado são entidades distintas;
13. item anunciado continua vindo do plano, item comprado vem do relatório;
14. as queries de valor por exposição, subnicho, item anunciado×comprado e integridade podem ser executadas;
15. nenhuma regra de score, quota, fallback, cooldown ou seleção editorial foi alterada por esta entrega.

## 14. Princípios e limites de interpretação

Não assumir que:

- `item_id` diferente significa conteúdo editorial diferente;
- alta venda histórica significa alto interesse no grupo;
- baixa venda direta significa publicação ruim;
- `clickTime` de conversão representa todos os cliques;
- `referrer` sozinho identifica a publicação;
- `productType` da Shopee equivale ao futuro `product_type` editorial;
- `attributionType` possui significado não confirmado;
- `validatedReport` deve substituir `conversionReport`;
- um `Sub_id` bruto do Click Report possui formato conhecido antes do teste empírico.

A pergunta final que esta arquitetura deve permitir responder é:

> **Quanto valor cada exposição do grupo produziu, de que forma produziu esse valor e o que isso ensina sobre o próximo produto que merece ocupar um slot?**

## 15. Fora de escopo

Continuam fora desta spec:

- alteração do `commercial_score`;
- redistribuição editorial baseada em cliques antes de acumular evidência;
- algoritmo do futuro `product_type` editorial;
- mudança das regras internas de refresh;
- mudança das regras internas do planner;
- redefinição da copy;
- interpretação não validada dos campos externos Shopee;
- automação do download do Click Report enquanto não houver mecanismo confirmado para isso.

Autenticação/assinatura da Shopee, retry e detalhes do cliente GraphQL são detalhes de implementação da integração e devem respeitar o contrato definido aqui sem ampliar o escopo funcional.

# Contrato operacional — Sync diário do `conversionReport` Shopee

Status: **normativo para a feature de tracking Shopee**.

Este documento complementa `11-spec-rastreamento-cliques-conversoes-shopee.md` e **deve obrigatoriamente ser implementado sob os limites definidos em `docs/projeto/11b-limites-implementacao-tracking-shopee.md`**.

Em caso de conflito entre este documento e `docs/projeto/11b-limites-implementacao-tracking-shopee.md`, **prevalece `11b`**. Em especial, este sync é uma criação nova e isolada da feature e não autoriza alteração de SQL existente, refresh, planner, n8n/publicação, score/editorial ou catálogo global.

## 1. Objetivo

O `conversionReport` deve ser coletado **automaticamente e diariamente na VPS** e persistido nas novas estruturas da feature.

Esse processo é novo e isolado. Ele não altera refresh, planner, n8n, publicação, SQL existente ou regras editoriais.

Fluxo:

```text
11:00 America/Sao_Paulo
        ↓
calcular dia anterior
00:00:00 → 23:59:59 America/Sao_Paulo
        ↓
converter limites para Unix timestamp em segundos
        ↓
invocar conversionReport
        ↓
paginar até hasNextPage=false
        ↓
persistir sync run + nodes + orders + items
        ↓
dados disponíveis para analytics
```

## 2. Horário

Contrato informado pela API/documentação usada no projeto: os dados do dia anterior ficam disponíveis a partir de **10:30 GMT-3**.

Decisão operacional:

```text
execução diária = 11:00 America/Sao_Paulo
```

O intervalo de 30 minutos é margem operacional entre a disponibilidade informada e a coleta.

O scheduler deve usar timezone explícito `America/Sao_Paulo`, sem depender do timezone configurado na VPS.

Se a VPS continuar configurada em UTC, 11:00 em `America/Sao_Paulo` corresponde atualmente a 14:00 UTC; isso é consequência operacional, não deve substituir o contrato de timezone da aplicação.

## 3. Janela de compra consultada

Cada execução consulta **somente o dia calendário anterior em `America/Sao_Paulo`**.

Exemplo conceitual para uma execução em 2026-08-27 às 11:00:

```text
purchaseTimeStart = 2026-08-26 00:00:00 America/Sao_Paulo
purchaseTimeEnd   = 2026-08-26 23:59:59 America/Sao_Paulo
```

Os valores enviados à API devem ser convertidos para **Unix timestamp em segundos**.

Não usar UTC 00:00–23:59 como definição do dia de negócio. Primeiro resolver o dia em `America/Sao_Paulo`, depois converter os dois limites para epoch.

## 4. Campos de entrada da API

### 4.1 Obrigatórios para a rotina diária do projeto

| Campo | Valor/regra |
| --- | --- |
| `purchaseTimeStart` | epoch em segundos de 00:00:00 do dia anterior em `America/Sao_Paulo` |
| `purchaseTimeEnd` | epoch em segundos de 23:59:59 do dia anterior em `America/Sao_Paulo` |
| `conversionStatus` | `ALL` |
| `categoryType` | `ALL` |
| `orderStatus` | `ALL` |
| `buyerType` | `ALL` |
| `productType` | `ALL` |
| `fraudStatus` | `ALL` |
| `device` | `ALL` |

A rotina diária deve buscar o universo do período e não restringir por produto, pedido, comprador, dispositivo ou status.

### 4.2 `productId`

`productId` **não deve ser enviado pela rotina diária**.

O valor usado anteriormente em testes era fictício e servia apenas para exploração da API. Filtrar por um produto impediria a coleta completa das conversões do dia.

### 4.3 Paginação

| Campo | Regra |
| --- | --- |
| `scrollId` | omitido/nulo na primeira chamada; nas chamadas seguintes usar o `pageInfo.scrollId` retornado pela página anterior quando `hasNextPage=true` |
| `limit` | pode ser configurado apenas dentro do valor aceito pelo schema real da API; não assumir um máximo não confirmado |

A sincronização só termina com sucesso quando:

```text
pageInfo.hasNextPage = false
```

O `scrollId` e os metadados de paginação devem ser persistidos em `offers.shopee_conversion_sync_runs` para auditoria.

## 5. Query lógica da rotina

Forma de referência:

```graphql
query DailyConversionReport(
  $purchaseTimeStart: Int!,
  $purchaseTimeEnd: Int!,
  $scrollId: String
) {
  conversionReport(
    purchaseTimeStart: $purchaseTimeStart,
    purchaseTimeEnd: $purchaseTimeEnd,
    conversionStatus: ALL,
    categoryType: ALL,
    orderStatus: ALL,
    buyerType: ALL,
    productType: ALL,
    fraudStatus: ALL,
    device: ALL,
    scrollId: $scrollId
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

Os tipos GraphQL exatos das variáveis devem seguir o schema exposto pelo Explorer/Open API no momento da implementação; a regra funcional deste documento são os campos e valores acima.

## 6. Outputs obrigatórios da request

Esta seção é **normativa**. A implementação não deve escolher livremente quais campos ignorar ou promover. Cada output solicitado do `conversionReport` tem um destino definido abaixo.

### 6.1 Campos do node/conversão — persistir em colunas explícitas

Os seguintes campos devem ser solicitados e persistidos em colunas da nova estrutura de conversões da feature:

| Output da API | Destino/uso |
| --- | --- |
| `clickTime` | coluna de clique convertido / cálculo de latência |
| `purchaseTime` | coluna de compra / definição temporal da conversão |
| `conversionId` | identidade externa, indexada mas não única isoladamente |
| `shopeeCommissionCapped` | composição da comissão |
| `sellerCommission` | composição da comissão |
| `totalCommission` | **KPI econômico principal** |
| `netCommission` | reconciliação/auditoria financeira |
| `buyerType` | segmentação futura |
| `utmContent` | raw de tracking e resolução futura de `dispatch_plan_id` |

Também deve existir a coluna interna `dispatch_plan_id`, preenchida quando `utmContent` permitir a resolução; ela não é output direto da API.

### 6.2 Campos do node/conversão — preservar no `raw_payload`

Os seguintes outputs devem continuar sendo solicitados porque fazem parte do payload observado e podem ser úteis para auditoria/evolução, mas **não precisam ser promovidos a colunas analíticas de primeira classe nesta fase**:

```text
mcnManagementFeeRate
mcnManagementFee
mcnContractId
linkedMcnName
device
productType
referrer
```

Se a tabela de conversões usar `raw_payload`, esses campos devem estar integralmente presentes nele. A implementação não deve descartá-los silenciosamente.

### 6.3 Campos de pedido — persistir em colunas explícitas

Cada `orders[]` deve preservar em colunas:

| Output da API | Destino/uso |
| --- | --- |
| `orderId` | identidade externa do pedido |
| `shopType` | estado/contexto comercial retornado pela Shopee |
| `orderStatus` | estado do pedido; necessário para leitura de conversão pendente/concluída/cancelada conforme valores reais da API |

O pedido deve referenciar o `conversion_record_id` técnico do node correspondente e preservar `conversion_id` quando necessário para auditoria.

### 6.4 Campos de item comprado — persistir em colunas explícitas

Os seguintes outputs de `orders[].items[]` são necessários para as análises centrais e devem ser colunas explícitas:

| Output da API | Destino/uso |
| --- | --- |
| `itemId` | item efetivamente comprado; comparação com `daily_dispatch_plan.item_id` para direta/indireta |
| `itemName` | leitura/auditoria |
| `itemPrice` | preço de referência retornado |
| `actualAmount` | valor efetivo da linha |
| `refundAmount` | ajuste/reembolso |
| `qty` | quantidade |
| `itemTotalCommission` | comissão da linha comprada |
| `globalCategoryLv1Name` | demanda/categoria comprada |
| `globalCategoryLv2Name` | demanda/categoria comprada |
| `globalCategoryLv3Name` | demanda/categoria comprada |
| `fraudStatus` | integridade/estado antifraude |
| `attributionType` | evidência externa de atribuição Shopee |
| `completeTime` | ciclo temporal do item/pedido |

### 6.5 Campos de item comprado — preservar no `raw_payload`

Os seguintes outputs devem continuar sendo solicitados e preservados no payload raw do item, sem necessidade de coluna analítica explícita nesta fase:

```text
shopId
shopName
promotionId
modelId
displayItemStatus
imageUrl
itemSellerCommission
itemSellerCommissionRate
itemShopeeCommissionCapped
itemShopeeCommissionRate
itemNotes
fraudReason
channelType
campaignPartnerName
campaignType
```

A preservação raw permite auditoria e futura promoção sem exigir alteração da API nem perda histórica.

### 6.6 Outputs de paginação — persistir no controle do sync

Os seguintes campos de `pageInfo` não são fatos analíticos de conversão; são controle obrigatório da coleta e devem ser persistidos em `offers.shopee_conversion_sync_runs`:

```text
page
limit
hasNextPage
scrollId
```

`hasNextPage` determina se uma nova chamada é necessária. `scrollId` deve alimentar a chamada seguinte quando aplicável.

### 6.7 Regra de completude

Uma execução diária só é considerada completa quando:

1. todos os campos obrigatórios definidos nesta seção foram solicitados na query;
2. todos os nodes retornados foram processados;
3. todos os `orders[]` e `items[]` foram processados;
4. todos os campos classificados como coluna foram persistidos na estrutura correspondente;
5. todos os campos classificados como raw foram preservados no `raw_payload` correspondente;
6. a paginação terminou com `hasNextPage=false`;
7. o `sync_run` registrou a janela, filtros e metadados de paginação.

Nenhum campo desta seção pode ser removido da request por conveniência de implementação sem revisão explícita desta spec.

## 7. Serviço na VPS

Criar serviço/timer novo e exclusivo da feature, por exemplo:

```text
shopee-conversion-report-sync.service
shopee-conversion-report-sync.timer
```

Responsabilidades do novo serviço:

1. resolver o dia anterior em `America/Sao_Paulo`;
2. calcular `purchaseTimeStart` e `purchaseTimeEnd`;
3. autenticar na Open API Shopee com as credenciais já disponibilizadas à integração;
4. executar `conversionReport`;
5. percorrer todas as páginas;
6. persistir somente nas tabelas novas da feature;
7. registrar sucesso/erro em `offers.shopee_conversion_sync_runs`.

Não alterar timer, service ou código interno do refresh/planner existentes para executar esse sync.

## 8. Idempotência diária

A mesma janela pode precisar ser reexecutada por falha operacional.

`shopee_conversion_sync_runs.query_filters` deve registrar no mínimo:

```json
{
  "timezone": "America/Sao_Paulo",
  "purchase_date": "YYYY-MM-DD",
  "purchaseTimeStart": 0,
  "purchaseTimeEnd": 0,
  "conversionStatus": "ALL",
  "categoryType": "ALL",
  "orderStatus": "ALL",
  "buyerType": "ALL",
  "productType": "ALL",
  "fraudStatus": "ALL",
  "device": "ALL"
}
```

Os zeros acima são placeholders documentais; a execução persiste os epochs reais.

Reexecução não pode duplicar fatos analíticos.

## 9. Correção de identidade observada no payload real

O payload real fornecido mostrou que `conversionId` **não identifica de forma única um node retornado**.

Foi observado o mesmo `conversionId = 241289038161544` em múltiplos nodes, cada um com `orderId` diferente e `totalCommission` diferente.

Consequência:

```text
conversion_id NÃO pode ser PK única da tabela que representa nodes da API
```

A tabela nova `offers.shopee_conversions` deve usar chave técnica própria, por exemplo:

| Coluna | Regra |
| --- | --- |
| `conversion_record_id` | `UUID PK` técnico |
| `conversion_id` | `TEXT/BIGINT NOT NULL`, indexado, não UNIQUE |
| `dispatch_plan_id` | `UUID NULL` resolvido de `utmContent` |
| demais campos do node | conforme spec |

`offers.shopee_conversion_orders` deve referenciar `conversion_record_id` e também preservar `conversion_id`/`order_id` conforme necessário para auditoria.

A idempotência deve considerar a estrutura efetivamente observada. Na primeira implementação, a combinação de `conversion_id + order_id` é a candidata natural para a identidade de pedido dentro de uma conversão, mas deve ser aplicada na tabela de pedidos, não transformando `conversion_id` isoladamente em chave única.

## 10. Relação com tracking por Sub IDs

Depois da implantação dos links rastreáveis, `utmContent` será preservado como raw e usado para resolver `dispatch_plan_id` quando o formato esperado estiver presente.

Conversões históricas com:

```text
utmContent = ----
```

continuam válidas e devem ser persistidas como não atribuídas a uma exposição específica.

## 11. KPI

Para analytics desta fase:

```text
KPI econômico principal = totalCommission
```

A coleta diária deve preservar também `sellerCommission`, `shopeeCommissionCapped` e `netCommission`, mas os relatórios de valor por exposição usam `totalCommission` como métrica principal.

## 12. Limites e referência normativa obrigatória

Este processo automático diário é uma **criação nova da feature** e está integralmente sujeito a:

```text
docs/projeto/11b-limites-implementacao-tracking-shopee.md
```

Em caso de dúvida sobre o que pode ou não ser modificado, **consultar `11b` e aplicar seus limites antes de qualquer implementação**.

Este documento não autoriza:

- alteração de SQL existente;
- alteração de refresh;
- alteração de planner;
- alteração de n8n/publicação;
- alteração de score/editorial;
- alteração de catálogo global;
- uso de `productId` como filtro fixo;
- execução de `validatedReport` enquanto `validationId` não estiver definido.

# Contrato operacional — Sync diário do `conversionReport` Shopee

Status: **normativo para a feature de tracking Shopee**.

Este documento complementa `11-spec-rastreamento-cliques-conversoes-shopee.md` e `11b-limites-implementacao-tracking-shopee.md`.

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

## 6. Serviço na VPS

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

## 7. Idempotência diária

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

## 8. Correção de identidade observada no payload real

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

## 9. Relação com tracking por Sub IDs

Depois da implantação dos links rastreáveis, `utmContent` será preservado como raw e usado para resolver `dispatch_plan_id` quando o formato esperado estiver presente.

Conversões históricas com:

```text
utmContent = ----
```

continuam válidas e devem ser persistidas como não atribuídas a uma exposição específica.

## 10. KPI

Para analytics desta fase:

```text
KPI econômico principal = totalCommission
```

A coleta diária deve preservar também `sellerCommission`, `shopeeCommissionCapped` e `netCommission`, mas os relatórios de valor por exposição usam `totalCommission` como métrica principal.

## 11. Limites

Este processo automático diário é uma **criação nova da feature**.

Ele não autoriza:

- alteração de SQL existente;
- alteração de refresh;
- alteração de planner;
- alteração de n8n/publicação;
- alteração de score/editorial;
- alteração de catálogo global;
- uso de `productId` como filtro fixo;
- execução de `validatedReport` enquanto `validationId` não estiver definido.

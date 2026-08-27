# Spec — Rastreamento de cliques, conversões e diversidade funcional na Shopee

Status: especificação funcional e técnica para instrumentação de rastreamento e base analítica. As regras comerciais/editoriais existentes permanecem preservadas. A modelagem de `product_type` continua como evolução futura.

## 1. Escopo técnico e orquestração diária

### 1.1 Objetivo

Evoluir a operação Shopee para relacionar deterministicamente:

1. o que foi planejado;
2. o que foi efetivamente publicado;
3. o que recebeu clique;
4. o que gerou conversão direta ou indireta;
5. quanto cada exposição gerou de comissão.

A instrumentação deve criar a base necessária para análises futuras de interesse, monetização e diversidade funcional sem substituir o `commercial_score` atual.

### 1.2 Decisão de orquestração

Hoje existem caminhos operacionais separados para:

- refresh de candidatos/ofertas Shopee;
- planejamento e persistência da fila diária em `offers.daily_dispatch_plan`.

Esta evolução deve consolidar a execução diária em **uma única orquestração sequencial**, composta por três estágios:

```text
1. Refresh Shopee existente
   ↓
2. Planejamento da fila diária existente
   ↓
3. Geração das short URLs rastreáveis
   ↓
4. Liberação da fila para consumo/publicação
```

A terceira etapa só pode ocorrer depois da criação de `offers.daily_dispatch_plan`, porque o `dispatch_plan_id` é parte obrigatória do rastreamento.

A consolidação é de **orquestração**, e não uma fusão monolítica dos componentes. Refresh e planner devem continuar testáveis e executáveis isoladamente para diagnóstico.

### 1.3 O que deve ser alterado

Devem ser alterados somente os pontos necessários para:

- criar uma operação diária única que execute refresh, planner e geração de tracking em ordem;
- gerar uma short URL Shopee para cada exposição planejada;
- persistir o resultado por `dispatch_plan_id`;
- liberar para publicação somente exposições com tracking válido;
- fazer a superfície consumida pelo publicador entregar a nova short URL no campo `offer_link` já esperado pela copy;
- criar estruturas de dados para Click Report e relatórios de conversão da Shopee.

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
- contrato atual de `publication_events` além das relações/campos estritamente necessários ao tracking;
- regras atuais de claim, consumo e registro do envio.

## 2. Fontes de dados já disponíveis

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
  -> Sub ID de exposição
  -> short URL específica da exposição
  -> publicação
  -> publication_events.publish_id
  -> Click Report
  -> conversionReport / validatedReport
```

## 3. Dados disponibilizados pela Shopee

### 3.1 Click Report

O Click Report é disponibilizado no portal, fora da Open API observada, e contém no mínimo:

- `ID dos Cliques`;
- `Tempo dos Cliques`;
- `Região dos Cliques`;
- `Sub_id`;
- `Referenciador`.

Esse relatório é a fonte de **todos os cliques reportados**, inclusive cliques sem conversão.

O arquivo já analisado possuía 48 cliques e todos estavam com `Sub_id = ----`; portanto os eventos históricos desse arquivo não podem ser reconciliados deterministicamente com uma exposição específica.

O `Referenciador` não deve ser usado como chave principal de atribuição.

### 3.2 `conversionReport`

O schema fornecido para `conversionReport` disponibiliza no nó de conversão, entre outros:

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

Pedidos incluem:

- `orderId`;
- `shopType`;
- `orderStatus`.

Itens comprados incluem, entre outros:

- `shopId`;
- `shopName`;
- `completeTime`;
- `promotionId`;
- `modelId`;
- `itemId`;
- `itemName`;
- `itemPrice`;
- `displayItemStatus`;
- `actualAmount`;
- `refundAmount`;
- `qty`;
- `imageUrl`;
- `itemTotalCommission`;
- `itemSellerCommission`;
- `itemSellerCommissionRate`;
- `itemShopeeCommissionCapped`;
- `itemShopeeCommissionRate`;
- `itemNotes`;
- `globalCategoryLv1Name`;
- `globalCategoryLv2Name`;
- `globalCategoryLv3Name`;
- `fraudStatus`;
- `fraudReason`;
- `attributionType`;
- `channelType`;
- `campaignPartnerName`;
- `campaignType`.

A paginação disponibiliza:

- `page`;
- `limit`;
- `hasNextPage`;
- `scrollId`.

`clickTime` neste relatório representa o clique associado à conversão e **não substitui o Click Report para medir todos os cliques**.

### 3.3 `validatedReport`

O `validatedReport` fornecido possui essencialmente o mesmo conjunto de campos de conversão, pedido e item, além da mesma estrutura de paginação.

Esta spec não presume uma diferença semântica baseada apenas no nome do endpoint. A implementação deve preservar a origem do dado (`conversionReport` ou `validatedReport`) para permitir comparação e reconciliação sem sobrescrever silenciosamente um estado pelo outro.

## 4. Contrato obrigatório de tracking e short URL

### 4.1 Momento de geração

A linha pode ser criada em `offers.daily_dispatch_plan` antes da existência da URL rastreável. Isso é necessário porque o próprio `dispatch_plan_id` participa da geração do tracking.

Porém, uma linha Shopee **não pode ser exposta como pronta para publicação** até a geração e persistência bem-sucedida da short URL rastreável.

Fluxo de estado conceitual:

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
  v_daily_dispatch_ready pode expor a linha ao publicador
```

Não deve existir fallback silencioso para publicação usando URL não rastreada.

### 4.2 URL de entrada e URL consumida pela copy

A entrada `originUrl` da API deve ser:

```text
offers.catalog_items.product_link
```

`product_link` é a URL canônica/original usada como entrada da geração do novo link.

A saída `shortLink` é a URL que deve ser usada pela publicação.

O fluxo operacional atual do n8n consome `offer_link` para montar a copy. Esse contrato deve ser preservado.

Portanto:

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

**Não sobrescrever globalmente `catalog_items.offer_link` com uma URL específica de `dispatch_plan_id`.** A short URL é propriedade da exposição planejada, pois contém identificação daquela publicação. Reutilizar o mesmo item em outro `dispatch_plan_id` deve gerar outra short URL.

A view/superfície pronta para publicação deve continuar entregando um campo denominado `offer_link`, porém esse valor deve vir da short URL rastreável persistida para o plano.

### 4.3 Quatro `Sub_ids` obrigatórios

O projeto utilizará exatamente quatro Sub IDs nesta fase:

| Posição | Conteúdo | Regra | Exemplo |
| --- | --- | --- | --- |
| `subId[0]` | meio atual | literal fixo para este fluxo | `wa` |
| `subId[1]` | perfil | valor de `daily_dispatch_plan.profile`, sem mapping manual | `feminino` |
| `subId[2]` | exposição planejada | `dp` + UUID de `dispatch_plan_id` sem hífens | `dp550e8400e29b41d4a716446655440000` |
| `subId[3]` | item anunciado | `daily_dispatch_plan.item_id` convertido para texto | `18797641257` |

A quinta posição aceita pela Shopee fica reservada e não deve ser preenchida nesta entrega.

O uso direto de `profile` é obrigatório para que novos profiles passem a ser identificados automaticamente sem tabela de abreviação (`fem`, `gest`, etc.).

### 4.4 Normalização do `dispatch_plan_id`

O UUID original **não deve ser alterado no Supabase**.

Somente sua representação enviada à Shopee é normalizada:

```text
550e8400-e29b-41d4-a716-446655440000
        ↓ remover '-'
550e8400e29b41d4a716446655440000
        ↓ prefixar 'dp'
dp550e8400e29b41d4a716446655440000
```

Regra formal:

```text
dispatch_tracking_id = "dp" + replace(dispatch_plan_id::text, "-", "")
```

Não usar underscore, hífen, truncamento ou hash nessa representação.

O formato completo acima foi validado em chamada real à API Shopee e aceito com sucesso.

### 4.5 Request validada

Contrato da API:

| Field | Type | Regra neste projeto |
| --- | --- | --- |
| `originUrl` | `String!` | obrigatório; `catalog_items.product_link` |
| `subIds` | `[String]` | exatamente quatro nesta entrega |

Exemplo validado:

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
  }
}
```

Resposta observada:

```json
{
  "data": {
    "generateShortLink": {
      "shortLink": "https://s.shopee.com.br/3g3DPzjYgO"
    }
  }
}
```

Isso fecha a decisão de formato do `dispatch_plan_id`: o UUID completo, sem hífens e com prefixo `dp`, cabe e foi aceito pela chamada testada.

### 4.6 Precondições para READY

Uma exposição Shopee somente pode ficar `READY` quando:

- existir `product_link` válida;
- `profile` estiver presente;
- `dispatch_plan_id` estiver presente;
- `item_id` estiver presente;
- os quatro Sub IDs forem produzidos conforme contrato;
- `generateShortLink` retornar uma `shortLink` válida;
- a short URL tiver sido persistida para aquele `dispatch_plan_id`.

Falha em qualquer requisito bloqueia somente a liberação daquela exposição; não autoriza fallback para URL sem tracking.

## 5. Saídas da preparação diária

Ao final da orquestração diária, cada exposição Shopee planejada deve possuir, no mínimo:

- `dispatch_plan_id` original;
- `profile`;
- `item_id`;
- `tracking_sub_ids` efetivamente enviados;
- `tracking_short_url` retornada;
- timestamp de geração;
- estado de tracking suficiente para determinar se a linha está ou não pronta;
- preservação de `product_link` como origem canônica.

Para o consumidor existente, a principal saída permanece:

```text
offer_link = tracking_short_url
```

na superfície `offers.v_daily_dispatch_ready` ou equivalente usada pelo publicador.

## 6. Alterações necessárias no Supabase

Esta seção define a modelagem mínima necessária. Nomes finais de constraints e detalhes de índices podem ser refinados na migração, mas a separação das entidades e suas responsabilidades faz parte desta spec.

### 6.1 Tracking por exposição em `offers.daily_dispatch_plan`

A URL rastreável pertence ao plano, não ao catálogo global.

Adicionar ao plano campos equivalentes a:

| Campo | Tipo sugerido | Finalidade |
| --- | --- | --- |
| `tracking_sub_ids` | `TEXT[]` | quatro Sub IDs enviados à Shopee |
| `tracking_short_url` | `TEXT` | `shortLink` retornada por `generateShortLink` |
| `tracking_generated_at` | `TIMESTAMPTZ` | quando a URL foi gerada |
| `tracking_status` | `TEXT` | estado técnico, por exemplo `pending`, `ready`, `failed` |
| `tracking_error` | `TEXT NULL` | diagnóstico da última falha, sem alterar regras comerciais |

Regras mínimas:

- `tracking_sub_ids` deve possuir exatamente quatro elementos quando `tracking_status = 'ready'`;
- `tracking_short_url` deve ser não nula quando `tracking_status = 'ready'`;
- `dispatch_plan_id` continua sendo a chave canônica;
- não criar um segundo UUID de publicação prévia;
- `catalog_items.product_link` não é modificado por essa etapa;
- `catalog_items.offer_link` não deve ser sobrescrito globalmente com links específicos de plano.

A `v_daily_dispatch_ready` deve exigir tracking válido para Shopee e projetar:

```text
offer_link := daily_dispatch_plan.tracking_short_url
```

Para marketplaces que não participem desta integração, a alteração não deve quebrar o comportamento existente.

### 6.2 Lotes de importação do Click Report

Como o Click Report é obtido fora da API, deve existir rastreabilidade de cada arquivo/importação.

Criar tabela equivalente a `offers.shopee_click_report_imports` com, no mínimo:

| Campo | Finalidade |
| --- | --- |
| `import_id UUID PK` | identidade do lote |
| `source_filename TEXT` | nome do arquivo importado |
| `source_sha256 TEXT` | idempotência/proveniência do arquivo |
| `imported_at TIMESTAMPTZ` | momento da ingestão |
| `row_count INTEGER` | quantidade de linhas processadas |
| `status TEXT` | estado da importação |
| `created_at TIMESTAMPTZ` | auditoria |

O mesmo arquivo não deve produzir eventos duplicados quando reprocessado.

### 6.3 Eventos de clique

Criar tabela equivalente a `offers.shopee_click_events`.

Campos mínimos conhecidos a partir do relatório fornecido:

| Campo | Tipo sugerido | Origem |
| --- | --- | --- |
| `click_id TEXT` | `TEXT` | `ID dos Cliques` |
| `click_time TIMESTAMPTZ` | `TIMESTAMPTZ` | `Tempo dos Cliques` |
| `click_region TEXT` | `TEXT` | `Região dos Cliques` |
| `sub_id_raw TEXT` | `TEXT` | `Sub_id` bruto |
| `referrer TEXT` | `TEXT` | `Referenciador` |
| `import_id UUID` | FK | lote do Click Report |
| `dispatch_plan_id UUID NULL` | FK resolvida | derivado do Sub ID quando reconhecido |
| `profile TEXT NULL` | derivado/auditável | Sub ID ou plano resolvido |
| `advertised_item_id BIGINT NULL` | derivado/auditável | quarto Sub ID |
| `created_at TIMESTAMPTZ` | auditoria | interno |

Regras:

- preservar sempre `sub_id_raw` e o referrer exatamente como recebidos, além dos campos resolvidos;
- `dispatch_plan_id` pode ser nulo para arquivos antigos ou Sub IDs desconhecidos;
- eventos históricos com `Sub_id = ----` permanecem válidos como cliques não atribuídos;
- não assumir que `click_id` representa usuário único; usar apenas como identidade do evento conforme o relatório;
- definir idempotência por `click_id` se testes confirmarem unicidade no relatório; até essa confirmação, preservar também `import_id` e permitir uma chave técnica interna.

### 6.4 Execuções de sincronização dos relatórios da API

Para preservar proveniência, paginação e reprocessamento, criar tabela equivalente a `offers.shopee_conversion_sync_runs`.

Campos mínimos:

- `sync_run_id UUID PK`;
- `report_type TEXT NOT NULL` com valores `conversion_report` ou `validated_report`;
- filtros/período solicitados em `JSONB`;
- `started_at TIMESTAMPTZ`;
- `finished_at TIMESTAMPTZ NULL`;
- `status TEXT`;
- `rows_received INTEGER`;
- último `scroll_id`/metadados de paginação quando aplicável;
- `error TEXT NULL`;
- `created_at TIMESTAMPTZ`.

Isso permite auditar de qual consulta da Shopee veio cada observação.

### 6.5 Conversões canônicas

Criar tabela equivalente a `offers.shopee_conversions` para a identidade e os atributos de nível de conversão.

Campos mínimos conhecidos:

- `conversion_id TEXT` — identidade fornecida pela Shopee;
- `click_time TIMESTAMPTZ NULL`;
- `purchase_time TIMESTAMPTZ NULL`;
- `utm_content TEXT NULL`;
- `buyer_type TEXT NULL`;
- `device TEXT NULL`;
- `product_type TEXT NULL` — **campo da Shopee no relatório de conversão; não confundir com o futuro `product_type` editorial desta operação**;
- `referrer TEXT NULL`;
- `shopee_commission_capped NUMERIC NULL`;
- `seller_commission NUMERIC NULL`;
- `total_commission NUMERIC NULL`;
- `net_commission NUMERIC NULL`;
- `mcn_management_fee_rate NUMERIC NULL`;
- `mcn_management_fee NUMERIC NULL`;
- `mcn_contract_id TEXT NULL`;
- `linked_mcn_name TEXT NULL`;
- `dispatch_plan_id UUID NULL` — resolvido a partir de `utm_content`/Sub ID quando possível;
- `advertised_item_id BIGINT NULL` — item anunciado recuperado do tracking;
- `first_seen_at TIMESTAMPTZ`;
- `last_seen_at TIMESTAMPTZ`;
- timestamps internos.

`conversion_id` deve ser a chave natural de reconciliação entre leituras, mas a ingestão não deve apagar a proveniência do endpoint que observou o dado.

### 6.6 Observações por relatório: `conversionReport` versus `validatedReport`

Como a diferença semântica final entre os dois endpoints ainda deve seguir a definição oficial da Shopee, **não sobrescrever silenciosamente um relatório com o outro**.

Criar tabela equivalente a `offers.shopee_conversion_observations`, relacionada a `conversion_id` e `sync_run_id`, contendo:

- `conversion_id`;
- `sync_run_id`;
- `report_type`;
- valores de comissão observados;
- demais campos mutáveis/status observados no nível da conversão;
- `observed_at`;
- `raw_payload JSONB` opcional para auditoria.

Essa tabela permite comparar o estado visto em `conversionReport` com o estado posteriormente visto em `validatedReport` sem inventar a semântica de validação.

Uma view futura poderá escolher o estado corrente/validado conforme regra formal posterior.

### 6.7 Pedidos de conversão

Como uma conversão contém pedidos, criar tabela equivalente a `offers.shopee_conversion_orders`.

Campos mínimos:

- chave técnica;
- `conversion_id` FK;
- `order_id TEXT`;
- `shop_type TEXT NULL`;
- `order_status TEXT NULL`;
- referência à observação/sync quando necessário;
- timestamps internos.

A chave de idempotência deve considerar pelo menos `conversion_id + order_id` e, caso estados sucessivos precisem ser preservados, a observação/sync correspondente.

### 6.8 Itens comprados

Como o item comprado pode ser diferente do item anunciado, os itens da conversão devem ficar em entidade própria, equivalente a `offers.shopee_conversion_items`.

Campos mínimos conhecidos:

- chave técnica;
- `conversion_id` FK;
- `order_id`/relação com pedido;
- `shop_id`;
- `shop_name`;
- `complete_time`;
- `promotion_id`;
- `model_id`;
- `item_id`;
- `item_name`;
- `item_price`;
- `display_item_status`;
- `actual_amount`;
- `refund_amount`;
- `qty`;
- `image_url`;
- `item_total_commission`;
- `item_seller_commission`;
- `item_seller_commission_rate`;
- `item_shopee_commission_capped`;
- `item_shopee_commission_rate`;
- `item_notes`;
- `global_category_lv1_name`;
- `global_category_lv2_name`;
- `global_category_lv3_name`;
- `fraud_status`;
- `fraud_reason`;
- `attribution_type`;
- `channel_type`;
- `campaign_partner_name`;
- `campaign_type`;
- referência à observação/sync quando necessário;
- timestamps internos.

Não deduzir o significado de `attribution_type`; armazenar o valor retornado e interpretar somente após observar valores reais/documentação oficial.

### 6.9 Relações analíticas esperadas

A modelagem deve permitir a cadeia:

```text
daily_dispatch_plan
  1 -> 0..1 publication_event
  1 -> 0..N click_events
  1 -> 0..N conversions
             1 -> N orders
             1 -> N purchased_items
```

Isso é necessário para distinguir:

- item anunciado;
- item efetivamente comprado;
- venda direta;
- venda de outro item/loja;
- comissão direta/indireta conforme a atribuição retornada pela Shopee.

## 7. `product_type` editorial — necessidade futura, não disponível hoje

Existe um conceito futuro desta operação chamado `product_type`: a função comercial/editorial do produto dentro do subnicho, por exemplo:

```text
skincare-facial -> serum
skincare-facial -> hidratante
lingerie-e-intimos -> calcinha
lingerie-e-intimos -> sutia
```

Esse campo **não existe hoje no Supabase** e não é requisito para esta instrumentação.

Sua origem permanece aberta. A hipótese atual é que ele venha a nascer como evolução do processo de descoberta/taxonomia, possivelmente usando:

- palavra-chave de descoberta;
- título do produto;
- subnicho;
- categorias Shopee;
- outras regras futuras de classificação.

Esta spec não fixa o algoritmo.

Importante: o `productType` devolvido pela Shopee em `conversionReport` é um dado externo do relatório e **não deve ser automaticamente equiparado ao futuro `product_type` editorial interno** sem validação semântica.

O futuro `product_type` editorial não ocupa um dos quatro Sub IDs atuais e, quando existir, deverá ser recuperável a partir do `dispatch_plan_id`.

## 8. Entradas e saídas formais

### 8.1 Entradas da preparação diária

A nova terceira etapa recebe dados já produzidos pelos processos existentes:

- `dispatch_plan_id`;
- `profile`;
- `item_id`;
- `marketplace`;
- `catalog_items.product_link`;
- demais dados já pertencentes ao plano/catálogo quando necessários para reconciliação.

### 8.2 Saída da geração de tracking

Para cada plano Shopee:

```text
dispatch_plan_id
tracking_sub_ids[4]
tracking_short_url
tracking_generated_at
tracking_status
```

### 8.3 Saída para o publicador

A superfície pronta deve continuar entregando os campos atuais esperados, inclusive:

```text
dispatch_plan_id
profile
item_id
offer_link
```

com:

```text
offer_link = tracking_short_url
```

Não exigir mudança de placeholder/campo da copy para consumir `product_link`.

## 9. Métricas de monitoramento

### 9.1 Exposição

- publicações por subnicho;
- publicações por `item_id`;
- distribuição por horário/slot;
- concentração de exposição;
- futuramente, concentração por `product_type` editorial.

### 9.2 Interesse

A partir do Click Report:

- cliques totais;
- cliques por publicação;
- cliques por `item_id` anunciado;
- cliques por `profile`;
- cliques por subnicho após join pelo `dispatch_plan_id`;
- latência publicação -> clique;
- percentual de cliques não atribuídos.

Enquanto não houver impressões confiáveis no WhatsApp, usar `cliques por publicação`, não denominar CTR.

### 9.3 Monetização

A partir de `conversionReport` e `validatedReport`:

- conversões atribuídas por exposição;
- comissão por exposição;
- comissão por clique;
- item anunciado versus item comprado;
- categorias efetivamente compradas;
- intervalo clique -> compra;
- diferenças entre observações de `conversionReport` e `validatedReport`;
- compras diretas/indiretas somente conforme os dados reais de atribuição retornados pela Shopee.

### 9.4 Integridade

Monitorar:

- 100% das novas exposições Shopee liberadas para publicação com quatro Sub IDs válidos;
- 100% com short URL rastreável persistida;
- Sub ID/`utmContent` não reconhecido;
- divergência entre quarto Sub ID e `daily_dispatch_plan.item_id`;
- `dispatch_plan_id` duplicado indevidamente;
- publicação sem plano;
- clique/conversão atribuído a plano inexistente;
- erros da geração de short URL;
- divergências de reconciliação entre relatórios.

## 10. Critérios de aceite

A evolução é considerada tecnicamente concluída para a fase de instrumentação quando:

1. existe uma operação única que executa refresh -> planner -> tracking em sequência;
2. os contratos funcionais do refresh e planner permanecem inalterados;
3. cada linha Shopee planejada possui `dispatch_plan_id` antes da chamada de tracking;
4. `originUrl` vem de `catalog_items.product_link`;
5. os quatro Sub IDs seguem exatamente `wa`, `profile`, `dp<uuid_sem_hifens>`, `item_id`;
6. o UUID original no Supabase não é alterado;
7. a `shortLink` é persistida por `dispatch_plan_id`;
8. `catalog_items.offer_link` não é sobrescrito globalmente com URL específica de publicação;
9. a superfície READY entrega a short URL rastreável no campo `offer_link` já consumido pela copy;
10. nenhuma exposição Shopee é liberada para publicação sem tracking válido;
11. `publication_events` continua reconciliável ao mesmo `dispatch_plan_id`;
12. existe modelo persistente para ingestão idempotente do Click Report;
13. existe modelo persistente para `conversionReport` e `validatedReport`, preservando a origem da observação;
14. pedidos e itens comprados são preservados separadamente da identidade da conversão;
15. nenhuma regra de score, quota, fallback, cooldown ou seleção editorial foi alterada por esta entrega.

## 11. Cadência de análise

### Diário

- publicações;
- cobertura de tracking;
- cliques atribuídos/não atribuídos;
- conversões recentes;
- comissão recente;
- falhas de reconciliação.

### Semanal

- cliques por publicação/subnicho;
- conversão e comissão por publicação;
- relação entre item anunciado e comprado;
- concentração de exposição;
- sinais de saturação.

Quando o `product_type` editorial existir, incluir Top 1 / Top 3 / Top 5 e desempenho por tipo funcional.

### Mensal

- subnichos geradores de tráfego;
- subnichos geradores de venda direta/indireta conforme atribuição real;
- exposição sem retorno proporcional;
- diferenças entre resultado operacional e validado;
- necessidade de revisão editorial/taxonômica.

## 12. Princípios e limites de interpretação

Não assumir que:

- `item_id` diferente significa conteúdo editorial diferente;
- alta venda histórica do produto significa alto interesse no grupo;
- baixa venda direta significa publicação ruim;
- `clickTime` do relatório de conversão representa todos os cliques;
- referrer sozinho identifica a publicação;
- `productType` da Shopee equivale ao futuro `product_type` editorial;
- `attributionType` possui significado não confirmado pelos valores/documentação da Shopee;
- `validatedReport` deve sobrescrever `conversionReport` sem uma regra formal.

As decisões futuras devem poder analisar separadamente:

```text
qualidade comercial
+ interesse observado
+ monetização atribuída
+ diversidade funcional futura
```

## 13. Fora de escopo

Continuam fora desta spec:

- alteração do algoritmo de `commercial_score`;
- nova distribuição editorial baseada em cliques;
- algoritmo/implementação do futuro `product_type` editorial;
- mudança das regras internas de refresh;
- mudança das regras internas do planner;
- redefinição da copy;
- interpretação inventada de campos Shopee ainda não validados.

Autenticação/assinatura da Shopee, retry e detalhes do cliente GraphQL são detalhes de implementação da integração e devem respeitar o contrato definido aqui sem ampliar o escopo funcional.
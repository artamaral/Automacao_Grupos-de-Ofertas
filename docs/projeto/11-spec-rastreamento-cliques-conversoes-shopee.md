# Spec — Rastreamento de cliques, conversões e diversidade funcional na Shopee

Status: necessidade funcional e analítica documentada. Esta especificação não implementa chamadas à API nem altera regras editoriais atuais.

## 1. Objetivo

Evoluir a análise da operação do grupo feminino para distinguir quatro dimensões hoje tratadas de forma incompleta:

1. o que foi planejado e publicado;
2. o que despertou interesse e gerou clique;
3. o que gerou venda direta ou indireta;
4. quanto cada publicação e cada tipo de produto gerou de comissão.

A motivação é evitar que a diversidade aparente por `item_id` esconda repetição funcional. Diferentes anúncios podem representar, para a cliente, o mesmo tipo de produto — por exemplo várias calcinhas ou vários séruns — e ocupar repetidamente posições editoriais mesmo sem gerar interesse proporcional.

O objetivo não é substituir o `commercial_score`, mas criar base de dados para futuramente equilibrar qualidade comercial, interesse real, diversidade e receita.

## 2. Fontes de dados já disponíveis

### 2.1 Supabase

O Supabase já registra os dados necessários para identificar o item planejado e reconciliar sua publicação.

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

O `dispatch_plan_id` é a chave preferencial para rastreamento antes do envio porque já existe no momento em que a exposição é planejada. O `publish_id` permanece como identificador do evento de publicação efetivamente registrado depois do envio.

A cadeia de identidade esperada é:

```text
dispatch_plan_id
  -> identificador de rastreamento enviado à Shopee
  -> publicação
  -> publication_event / publish_id
  -> clique
  -> conversão
```

## 3. Dados disponibilizados pela Shopee

### 3.1 Click Report

O relatório de cliques disponibilizado pelo portal da Shopee contém, no mínimo:

- ID do clique;
- horário do clique;
- região do clique;
- `Sub_id`;
- referenciador.

Esse relatório é a fonte para medir interesse e tráfego, incluindo cliques que não resultaram em conversão.

O relatório atualmente observado ainda apresenta `Sub_id = ----` nos registros existentes, portanto os cliques atuais não podem ser relacionados deterministicamente a uma publicação específica.

### 3.2 `conversionReport`

A Shopee disponibiliza, entre outros, os seguintes campos:

- `clickTime`;
- `purchaseTime`;
- `conversionId`;
- `shopeeCommissionCapped`;
- `sellerCommission`;
- `totalCommission`;
- `netCommission`;
- `buyerType`;
- `utmContent`;
- `device`;
- `productType`;
- `referrer`;
- dados de pedido e itens comprados.

Para cada item comprado estão disponíveis, entre outros:

- `shopId`;
- `shopName`;
- `itemId`;
- `itemName`;
- `itemPrice`;
- `actualAmount`;
- `refundAmount`;
- `qty`;
- `itemTotalCommission`;
- `itemSellerCommission`;
- `itemSellerCommissionRate`;
- `itemShopeeCommissionCapped`;
- `itemShopeeCommissionRate`;
- `globalCategoryLv1Name`;
- `globalCategoryLv2Name`;
- `globalCategoryLv3Name`;
- `fraudStatus`;
- `fraudReason`;
- `attributionType`;
- `channelType`;
- `campaignPartnerName`;
- `campaignType`.

### 3.3 `validatedReport`

O `validatedReport` disponibiliza praticamente o mesmo conjunto de dados de conversão, incluindo `clickTime`, `purchaseTime`, `conversionId`, `utmContent`, comissões, pedidos, itens, categorias e `attributionType`.

A diferença operacional exata entre `conversionReport` e `validatedReport` deve ser tratada conforme a documentação oficial da Shopee. Esta spec não presume uma semântica adicional além dos campos observados.

## 4. Contrato obrigatório de rastreamento por `Sub_id`

### 4.1 Princípio

O identificador usado para rastreamento precisa existir antes da publicação. Por isso o `publish_id`, gerado apenas no registro posterior do envio, não deve ser usado como chave primária de rastreamento pré-publicação.

A chave canônica para essa finalidade é o `dispatch_plan_id`.

### 4.2 Quatro `Sub_ids` obrigatórios

Toda oferta Shopee rastreada deve possuir quatro `Sub_ids` obrigatórios antes de ser considerada pronta para publicação:

| Posição | Conteúdo | Origem | Exemplo |
| --- | --- | --- | --- |
| `subId[0]` | canal | contexto operacional | `wa` |
| `subId[1]` | perfil | `daily_dispatch_plan.profile` normalizado | `fem` |
| `subId[2]` | exposição planejada | `dispatch_plan_id` | `dp_8f31c2...` |
| `subId[3]` | item Shopee anunciado | `daily_dispatch_plan.item_id` | `23298157281` |

Exemplo conceitual:

```text
[
  "wa",
  "fem",
  "dp_8f31c2...",
  "23298157281"
]
```

A quinta posição permitida pela Shopee deve permanecer reservada para uma necessidade futura real. Não deve ser preenchida apenas porque está disponível.

### 4.3 Regra de bloqueio

Para uma oferta Shopee rastreada, não deve existir fallback silencioso para publicação sem rastreamento.

A oferta somente pode ser considerada pronta quando existirem:

- `originUrl` válida;
- canal;
- perfil;
- `dispatch_plan_id`;
- `item_id`.

Se qualquer um desses valores não puder ser determinado, o item não deve entrar na fila pronta para publicação rastreada.

### 4.4 Por que manter quatro valores se `dispatch_plan_id` já é suficiente

Tecnicamente o `dispatch_plan_id` já permite recuperar os demais dados no Supabase. Os outros três valores são mantidos para auditabilidade e resiliência dos relatórios brutos da Shopee.

Ao ler uma linha de relatório deve ser possível identificar diretamente:

- o canal;
- o perfil;
- a exposição planejada;
- o `item_id` anunciado.

Informações analíticas mais ricas, como subnicho, score e futuras classificações funcionais, devem permanecer no Supabase e ser recuperadas por relacionamento.

## 5. Contrato de entrada para geração da short URL

A geração da short URL exige os seguintes campos de entrada:

| Field | Type | Description |
| --- | --- | --- |
| `originUrl` | `String!` | URL original da oferta |
| `subIds` | `[String]` | Lista com os Sub IDs enviados em `utm_content`; a Shopee aceita até cinco |

Para este projeto, o contrato funcional é mais restritivo que o tipo genérico da API:

```text
originUrl: obrigatório
subIds: exatamente 4 valores obrigatórios nesta fase
```

Padrão conceitual da request:

```graphql
mutation {
  generateShortLink(input: {
    originUrl: "<ORIGINAL_URL>",
    subIds: [
      "<CHANNEL>",
      "<PROFILE>",
      "<DISPATCH_TRACKING_ID>",
      "<ITEM_ID>"
    ]
  }) {
    shortLink
    longLink
  }
}
```

Esta especificação define apenas o contrato de dados. Ficam fora de escopo:

- autenticação;
- assinatura da requisição;
- implementação da chamada;
- node/workflow responsável;
- retry;
- tratamento técnico de erro da integração.

Esses pontos serão especificados separadamente.

## 6. Dados que ainda faltam no Supabase

A estrutura atual não registra de forma própria os eventos do Click Report nem as conversões importadas da Shopee.

A necessidade futura é armazenar, no mínimo, os seguintes dados.

### 6.1 Rastreamento da fila/publicação

Deve ser possível persistir e reconciliar o identificador usado nos `Sub_ids` com:

- `dispatch_plan_id`;
- `publication_event_id`/`publish_id` quando a publicação existir;
- `item_id` anunciado;
- canal;
- perfil.

A forma física exata — coluna dedicada, view ou estrutura relacionada — deve ser definida na implementação, preservando `dispatch_plan_id` como chave canônica pré-publicação.

### 6.2 Eventos de clique

Devem ser persistíveis, no mínimo:

- `click_id`;
- `click_time`;
- `click_region`;
- `sub_id`/identificador recebido;
- `referrer`;
- referência resolvida ao `dispatch_plan_id` quando possível.

### 6.3 Conversões

Devem ser persistíveis, no mínimo:

- `conversion_id`;
- `click_time`;
- `purchase_time`;
- `utm_content`;
- `buyer_type`;
- `device`;
- `referrer`;
- `attribution_type`;
- `total_commission`;
- `net_commission`;
- demais dados de comissão relevantes;
- pedidos e itens comprados;
- categorias Shopee;
- status/fraude quando fornecidos;
- referência resolvida ao `dispatch_plan_id` quando possível.

A modelagem física dessas entidades deve ser especificada separadamente antes de qualquer migração.

## 7. `product_type` — necessidade futura, não disponível hoje

`product_type` representa a função comercial/funcional de um produto dentro do subnicho.

Exemplos conceituais:

```text
skincare-facial -> serum
skincare-facial -> hidratante
skincare-facial -> protetor-solar
lingerie-e-intimos -> calcinha
lingerie-e-intimos -> sutia
lingerie-e-intimos -> camisola
```

Esse conceito é necessário para detectar repetição funcional, porque `item_id`s diferentes podem representar essencialmente o mesmo tipo de produto para a cliente.

### Situação atual

`product_type` não existe hoje no Supabase e não deve ser tratado como dado já disponível.

Também não deve ser requisito para iniciar o rastreamento de cliques e conversões desta spec.

### Origem futura

A forma de obtenção de `product_type` permanece deliberadamente aberta.

A hipótese principal é que ele nasça como evolução do processo de descoberta/taxonomia, provavelmente usando combinações de:

- palavras-chave de descoberta;
- título do produto;
- taxonomia/subnicho;
- categorias retornadas pela Shopee;
- outras regras futuras de classificação.

Esta spec não fixa o algoritmo nem a fonte definitiva.

Quando essa evolução for especificada, o valor deverá ser estável o suficiente para análises históricas e poderá ser persistido também como snapshot na fila planejada para preservar a classificação usada no momento da decisão editorial.

`product_type` não ocupa um dos quatro `Sub_ids` atuais. Quando existir, deverá ser recuperável pelo `dispatch_plan_id` no Supabase.

## 8. Métricas de monitoramento

O monitoramento deve separar exposição, interesse e monetização.

### 8.1 Exposição

A partir do Supabase:

- publicações por subnicho;
- publicações por `item_id`;
- concentração dos itens publicados;
- distribuição por horário/slot;
- quando `product_type` existir, concentração por tipo funcional.

### 8.2 Interesse

A partir do Click Report:

- cliques totais;
- cliques por publicação;
- cliques por `item_id` anunciado;
- cliques por perfil/canal;
- cliques por subnicho após relacionamento com o Supabase;
- quando `product_type` existir, cliques por tipo funcional.

Enquanto não houver uma medida confiável de impressões individuais no WhatsApp, deve-se preferir `cliques por publicação` a chamar essa métrica de CTR.

### 8.3 Monetização

A partir de `conversionReport` e/ou `validatedReport`:

- conversões atribuídas por publicação;
- compras diretas e indiretas conforme os dados de atribuição da Shopee;
- comissão direta;
- comissão indireta;
- comissão total por publicação;
- comissão por clique;
- intervalo publicação -> clique convertido;
- intervalo clique -> compra;
- categorias dos itens efetivamente comprados.

### 8.4 Integridade do rastreamento

Deve ser monitorado continuamente:

- percentual de publicações Shopee com quatro `Sub_ids` válidos;
- cliques com `Sub_id` vazio ou não reconhecido;
- `utmContent` sem correspondência com `dispatch_plan_id`;
- divergência entre `item_id` anunciado no Sub ID e o item da fila;
- publicação efetiva sem relacionamento com a exposição planejada;
- duplicidade indevida de identificadores de exposição.

O objetivo de cobertura para novas publicações rastreadas é 100%.

## 9. Cadência de análise

### Diário

Monitorar:

- volume de publicações;
- volume de cliques;
- cobertura de `Sub_id`;
- cliques não atribuídos;
- conversões e comissão recentes;
- falhas de reconciliação.

### Semanal

Analisar:

- cliques por publicação e subnicho;
- conversão e comissão por publicação;
- concentração de exposição;
- relação entre itens anunciados e itens comprados;
- indícios de saturação ou baixa capacidade de gerar interesse.

Quando `product_type` existir, incluir concentração Top 1 / Top 3 / Top 5 e desempenho por tipo funcional.

### Mensal

Revisar:

- quais subnichos geram tráfego;
- quais geram vendas diretas;
- quais geram vendas indiretas;
- quais ocupam exposição sem retorno proporcional;
- necessidade de revisão editorial/taxonômica.

## 10. Princípios para análise

Não assumir que:

- `item_id` diferente significa conteúdo editorial diferente;
- alta quantidade de vendas históricas do produto significa alto interesse no grupo;
- baixa venda direta significa necessariamente publicação ruim;
- `clickTime` presente em conversão representa todos os cliques;
- referenciador sozinho identifica de forma confiável a publicação de origem;
- `product_type` já está disponível no catálogo atual.

As decisões futuras de seleção deverão considerar separadamente:

```text
qualidade comercial
+ interesse observado
+ monetização direta/indireta
+ diversidade funcional
```

sem substituir evidência por inferência.

## 11. Fora de escopo desta spec

Não fazem parte deste documento:

- implementação da chamada `generateShortLink`;
- autenticação/assinatura da Shopee;
- definição do workflow/nó responsável;
- automação da obtenção do Click Report;
- migrações SQL específicas;
- algoritmo futuro de `product_type`;
- alteração imediata do `commercial_score`;
- nova regra de distribuição editorial baseada em cliques.

Esses itens devem ser tratados em especificações próprias após a instrumentação e disponibilidade dos dados.
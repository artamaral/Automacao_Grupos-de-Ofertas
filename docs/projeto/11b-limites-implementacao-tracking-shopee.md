# Limites normativos de implementação — Tracking Shopee

Status: **normativo para a implementação da feature de tracking Shopee**.

Este documento restringe a implementação descrita em `11-spec-rastreamento-cliques-conversoes-shopee.md`. Em caso de conflito, estes limites prevalecem. O contrato do sync automático de conversões está detalhado em `11c-sync-diario-conversion-report-shopee.md`.

## 1. Regra principal

A feature deve ser **aditiva, isolada e de baixo impacto**.

> Nada existente deve ter sua lógica funcional alterada. Só são permitidas criações específicas desta feature e, em tabelas existentes, adição de novas colunas estritamente necessárias.

A única mudança permitida **na cadeia operacional existente de publicação** é conectar, em sequência, os processos já existentes de refresh e fila ao novo processo de geração do link afiliado rastreável com **Sub IDs**.

Além disso, fica autorizada uma segunda criação isolada da feature: um **sync automático diário de `conversionReport`**, executado na VPS e persistindo somente nas novas estruturas analíticas da feature. Esse sync não altera nem participa da execução de refresh/planner/publicação.

Onde houver referência anterior a `shopId` neste contexto, deve ser entendida como **Sub ID**. `shopId` não faz parte do contrato de geração do link rastreável desta feature.

## 2. Integração operacional permitida na publicação

O fluxo permitido é:

```text
REFRESH SHOPEE EXISTENTE
        ↓
PLANNER / FILA EXISTENTE
        ↓
GERAÇÃO DO LINK AFILIADO COM SUB IDs
        ↓
LIBERAÇÃO PARA PUBLICAÇÃO
```

A integração deve ser um novo orquestrador ou wrapper que execute os componentes existentes em sequência.

Os componentes de refresh e planner devem ser tratados como caixas-pretas:

```text
run_refresh_existente()
        ↓
run_planner_existente()
        ↓
run_generate_tracked_short_links()
```

A implementação da feature não pode refatorar, fundir ou reimplementar internamente refresh ou planner.

### 2.1 Processo automático adicional autorizado — `conversionReport`

Separadamente da cadeia de publicação, criar um serviço/timer novo da feature:

```text
11:00 America/Sao_Paulo
        ↓
conversionReport do dia anterior
purchaseTimeStart 00:00:00
purchaseTimeEnd   23:59:59
        ↓
novas tabelas de conversão
```

O contrato informado para a integração estabelece disponibilidade dos dados do dia anterior a partir de 10:30 GMT-3; a execução às 11:00 cria margem operacional de 30 minutos.

Esse serviço:

- é novo;
- roda diariamente na VPS;
- usa timezone explícito `America/Sao_Paulo`;
- consulta somente o dia calendário anterior;
- pagina até `hasNextPage=false`;
- não usa `productId` na coleta diária;
- grava somente nas novas tabelas da feature;
- não modifica timer/service/código interno de refresh ou planner.

## 3. Processos existentes que não podem ser alterados

### 3.1 Refresh Shopee

Não alterar:

- queries existentes;
- critérios de candidatos;
- limites/políticas;
- regras `FRESH`/`STALE`;
- snapshots;
- estabilidade;
- scoring;
- elegibilidade;
- comportamento de persistência;
- contratos de entrada/saída internos.

### 3.2 Planner / fila diária

Não alterar:

- queries existentes;
- `commercial_score`;
- pesos;
- quotas;
- distribuição editorial;
- rotação;
- fallback;
- cooldown;
- taxonomia/subnichos;
- número de slots;
- horários;
- sequenciamento;
- elegibilidade;
- regra atual de criação/substituição da fila.

### 3.3 Publicador / n8n / WhatsApp

Não alterar:

- copy;
- placeholders da mensagem;
- allowlist;
- grupo/destino;
- WAHA;
- claim;
- consumo;
- envio;
- registro do envio;
- regras de erro existentes;
- lógica editorial.

Se for necessário mudar a superfície de leitura da fila para incluir o link rastreável, isso faz parte **da integração operacional permitida** e deve se limitar à troca da origem dos dados por uma nova superfície criada por esta feature. Nenhuma outra lógica do publicador pode ser modificada.

## 4. Regra para SQL e Supabase

### 4.1 SQL existente

Nenhum SQL existente deve ser editado, reescrito ou substituído.

Isso inclui:

- views existentes;
- functions existentes;
- triggers existentes;
- procedures existentes;
- queries existentes usadas por refresh/planner;
- constraints existentes;
- índices existentes;
- tipos de colunas existentes;
- PKs/FKs existentes.

### 4.2 Única alteração permitida em tabelas existentes

Em tabelas existentes, somente:

```sql
ALTER TABLE ... ADD COLUMN ...
```

para colunas estritamente necessárias à feature.

Nenhuma coluna existente pode ser removida, renomeada, ter tipo alterado ou significado funcional modificado.

### 4.3 Criações novas permitidas

A feature pode criar recursos novos e isolados, por exemplo:

- novas tabelas de tracking/cliques/conversões;
- novos índices apenas sobre recursos criados pela feature ou novas colunas da feature;
- novas views específicas da feature;
- novo código cliente da API Shopee;
- novo importador do Click Report;
- novo orquestrador `refresh → planner → tracking`;
- novo serviço/timer diário de `conversionReport`;
- novos testes da feature;
- novos scripts/serviços próprios da feature.

Recursos novos não podem alterar o comportamento interno dos processos existentes.

## 5. Colunas aditivas permitidas no plano

A proposta mínima em `offers.daily_dispatch_plan` permanece aditiva:

| Coluna | Finalidade |
| --- | --- |
| `tracking_sub_ids` | quatro Sub IDs enviados à Shopee |
| `tracking_short_url` | `shortLink` retornada |
| `tracking_generated_at` | auditoria |
| `tracking_status` | estado técnico da geração |
| `tracking_error` | diagnóstico da geração |

Essas colunas não podem alterar score, seleção, ordem ou estado editorial do plano.

## 6. Contrato dos Sub IDs

A geração do link rastreável usa exatamente quatro Sub IDs nesta fase:

```text
subId[0] = "wa"
subId[1] = daily_dispatch_plan.profile
subId[2] = "dp" + dispatch_plan_id sem hífens
subId[3] = item_id como texto
```

Exemplo:

```text
wa
feminino
dp550e8400e29b41d4a716446655440000
18797641257
```

`shopId` não participa deste contrato.

## 7. Verificação da superfície READY atual

Foi verificada a definição real de `offers.v_daily_dispatch_ready` no Supabase.

Ela atualmente projeta:

```text
ranking.offer_link
```

proveniente de `offers.v_offer_ranking_current`.

Portanto, apenas adicionar `tracking_short_url` em `daily_dispatch_plan` **não faz a view existente passar a devolver automaticamente o novo link**.

Como esta feature não pode alterar SQL existente, `offers.v_daily_dispatch_ready` deve permanecer intacta.

A solução compatível com este contrato é criar uma **nova superfície específica da feature**, por exemplo:

```text
offers.v_daily_dispatch_ready_tracked
```

ou nome equivalente, construída apenas com SQL novo da feature.

Essa nova superfície deve preservar o contrato de campos esperado pelo publicador, mas fornecer:

```text
offer_link = daily_dispatch_plan.tracking_short_url
```

para exposições Shopee rastreadas.

A eventual troca da origem lida pelo publicador para essa nova superfície é considerada parte da integração operacional autorizada. Não autoriza qualquer outra alteração no publicador.

## 8. Catálogo global

Não sobrescrever `offers.catalog_items.offer_link` com short URL específica de uma exposição.

A short URL rastreável pertence ao `dispatch_plan_id`, não ao item global do catálogo.

Reutilizar o mesmo item em outra exposição deve poder gerar outra short URL sem modificar o histórico ou o significado global do catálogo.

## 9. Click Report manual

O Click Report continua sendo uma operação manual.

O operador é responsável por:

1. baixar o relatório no Portal/Central do Afiliado;
2. preservar o arquivo original;
3. preparar o arquivo no formato de importação definido pelo projeto;
4. separar/validar os quatro Sub IDs quando presentes;
5. entregar somente arquivo aderente ao contrato de entrada.

O importador da feature deve ser estrito:

- não adivinhar delimitadores;
- não inferir formatos alternativos;
- não corrigir automaticamente Sub IDs;
- não completar valores ausentes;
- rejeitar arquivo fora do layout definido;
- preservar raw suficiente para auditoria.

Registros legados com `Sub_id = ----` podem ser importados como raw clicks não atribuídos.

## 10. Estruturas novas de dados permitidas

As seguintes tabelas são criações próprias da feature e não alteram tabelas operacionais existentes:

```text
offers.shopee_click_report_imports
offers.shopee_click_events
offers.shopee_conversion_sync_runs
offers.shopee_conversions
offers.shopee_conversion_orders
offers.shopee_conversion_items
```

O payload real confirmou que `conversionId` pode aparecer em múltiplos nodes associados a pedidos distintos. Portanto `conversion_id` não deve ser declarado PK/UNIQUE isoladamente na tabela de nodes. O detalhe de identidade e idempotência está em `11c-sync-diario-conversion-report-shopee.md`.

`validatedReport` não faz parte do caminho crítico inicial e não deve ampliar a primeira implementação enquanto o fluxo de `validationId` não estiver definido.

## 11. Critério de revisão de qualquer mudança

Antes de aceitar qualquer alteração de implementação, aplicar estas perguntas:

1. É uma criação nova exclusiva da feature?
2. Se toca tabela existente, é somente `ADD COLUMN`?
3. Altera alguma query, view, trigger, function ou constraint existente? Se sim, **não permitido**.
4. Altera lógica de refresh ou planner? Se sim, **não permitido**.
5. Altera copy, claim, envio, WAHA ou regras do n8n? Se sim, **não permitido**.
6. Na cadeia de publicação, a mudança é estritamente necessária para encadear refresh → planner → link afiliado com Sub IDs → publicação? Se não, **fora de escopo**.
7. Fora da cadeia de publicação, a mudança é estritamente necessária ao sync diário isolado de `conversionReport` ou à ingestão/analytics da feature? Se não, **fora de escopo**.

## 12. Resultado esperado

A implementação deve adicionar tracking e analytics sem provocar regressão ou mudança comportamental nos fluxos atuais.

Em resumo:

```text
EXISTENTE permanece EXISTENTE
+
NOVAS COLUNAS mínimas
+
NOVAS TABELAS/VIEW/CÓDIGO da feature
+
INTEGRAÇÃO sequencial refresh → fila → link com Sub IDs
+
SYNC diário isolado de conversionReport às 11:00 America/Sao_Paulo
```

Nada além disso é autorizado por esta feature.

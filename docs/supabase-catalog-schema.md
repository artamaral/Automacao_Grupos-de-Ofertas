# Schema de catalogo e ranking no Supabase

Este documento descreve a fundacao de dados aplicada ao Supabase para receber
os catalogos curados localmente e produzir o ranking comercial.

## Status

Migration aplicada:

```text
supabase/migrations/202606290001_catalog_and_score.sql
```

Objetos criados no schema `offers`:

- `catalog_imports`;
- `catalog_item_import_history`;
- `catalog_items`;
- `offer_selection_state`;
- `publication_events`;
- `candidate_refresh_policies`;
- `offer_snapshots`;
- `offer_refresh_attempts`;
- `schema_migrations`;
- `v_offer_ranking_current`;
- `v_offer_latest_snapshot`;
- `v_offer_refresh_status`;
- `v_offer_scoring_current`;

Configuracao operacional aplicada ao banco:

- timezone padrao do database `postgres`: `America/Sao_Paulo`.

Migrations complementares:

```text
supabase/migrations/202608090002_set_database_timezone_sao_paulo.sql
supabase/migrations/202608110001_candidate_refresh_snapshots.sql
supabase/migrations/202608130001_incremental_discovery_catalog.sql
supabase/migrations/202608140001_publication_cooldown_2d.sql
supabase/migrations/202608150001_daily_dispatch_fresh_only.sql
```

Migrations versionadas para aplicacao da feature Instagram:

```text
supabase/migrations/202608150002_offer_media_assets.sql
supabase/migrations/202608150003_instagram_media_ready_view.sql
```

A migration incremental foi aplicada e o estado operacional vigente de
`2026-08-15` deve ser lido assim:

- `offers.v_offer_ranking_current` e a superficie de elegibilidade que alimenta
  o planejador diario, mas o planner do `feminino` persiste somente itens
  `refresh_status='FRESH'`;
- `offers.daily_dispatch_plan` e `offers.v_daily_dispatch_ready` governam o
  consumo horario do `feminino`, com a view revalidando freshness no momento do
  claim;
- confirmacoes novas alimentam `offers.offer_selection_state` e governam a
  reentrada do item por `cooldown_until`;
- o fluxo anterior em que o n8n consumia diretamente
  `offers.v_offer_ranking_current` ficou como legado.

Os campos temporais continuam usando `timestamptz`. A configuracao de timezone
altera a exibicao e interpretacao padrao das sessoes novas do Postgres, sem
reescrever os instantes ja gravados.

Os tres catalogos reais foram importados e ativados em `2026-06-29`. A
validacao isolada da formula de score tambem usa uma fixture transacional que e
revertida ao final do teste.

## Carga operacional validada

| Profile | Linhas | Subnichos | SHA-256 |
| --- | ---: | ---: | --- |
| `auto-e-moto` | 11.560 | 10 | `389873b60e6f...` |
| `feminino` | 27.292 | 31 | `ddf26fa26018...` |
| `mae-e-bebe` | 7.164 | 39 | `1c27182e6ebe...` |
| **Total** | **46.016** | **80 somados** |  |

Atualizacao em `2026-08-11`:

| Profile | Linhas antes | Removidas | Linhas ativas | Subnichos | Import ID | SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `feminino` | 27.292 | 2.090 | 25.202 | 31 | `d94d30be-576b-41a4-a504-cad83e69cec1` | `4504ca7a7b62...` |

A remocao aplicada no catalogo ativo `feminino/shopee` eliminou ofertas cujos
campos textuais continham `infantil` ou `juvenil`. A verificacao apos ativacao
confirmou:

- `row_count = 25.202`;
- `offers.catalog_items` ativo com `25.202` linhas;
- `offers.v_offer_ranking_current` retornando `25.202` linhas para `feminino`;
- `forbidden_rows = 0` para `infantil` e `juvenil`.

Antes do refactor incremental, para cada profile, a auditoria confirmou:

- `row_count` declarado igual ao total armazenado;
- total armazenado igual ao total retornado pela view;
- todos os itens elegiveis no momento da carga;
- `rank_profile` continuo, sem lacunas ou duplicacoes;
- hash local igual ao hash registrado no Supabase;
- uma unica importacao ativa por `profile + marketplace` no modelo anterior.

A segunda execucao de `feminino` reutilizou o mesmo `import_id`, comprovando que
o hash impede duplicacao da carga.

## Fronteira operacional

A descoberta, limpeza e curadoria continuam locais.

Fontes validadas:

```text
catalogs/clean/feminino/clean_catalog_rating_4_8_plus.csv
catalogs/clean/mae-e-bebe/clean_catalog_rating_4_8_plus.csv
catalogs/clean/auto-e-moto/clean_catalog_rating_4_8_plus.csv
```

Somente esses artefatos curados, ou futuras versoes validadas do mesmo
contrato, podem ser publicados no Supabase.

## catalog_imports

Registra cada rodada controlada de discovery/importacao incremental.

Controles principais:

- `profile`;
- `marketplace`;
- `source_path`;
- `source_sha256`;
- `source_modified_at`;
- `observed_at`;
- `row_count`;
- `status`;
- `validation_summary`;
- `imported_by`;
- `imported_at`;
- `activated_at` e `superseded_at`, preservados apenas como auditoria legada;
- `rejected_at`;
- `rejection_reason`.

Estados vigentes depois da migration incremental:

```text
completed
rejected
```

Nao existe ativacao nem substituicao integral de catalogo. Uma rodada e
idempotente por:

```text
profile + marketplace + source_sha256 + observed_at
```

O mesmo arquivo observado novamente em outro instante gera uma nova rodada e
novos snapshots. Um retry com a mesma chave reutiliza a rodada existente.

## catalog_items

Preserva o cadastro curado e cumulativo de cada item. A identidade e:

```text
profile + marketplace + item_id
```

`import_id` passa a indicar a primeira rodada em que o item entrou no profile.
Quando o mesmo item reaparece, nome cadastral, `stable_key` e `subniches` nao
sao alterados automaticamente; a nova observacao vai para `offer_snapshots`.

Campos normalizados:

- identidade: `stable_key`, `item_id`, `profile`, `marketplace`;
- produto: `product_name`, `product_link`, `offer_link`, `image_url`;
- preco: `price`, `reference_price`;
- sinais comerciais: `sales_count`, `rating`, `shop_type_codes`;
- comissao: `seller_commission_rate`, `shopee_commission_rate`,
  `commission_rate_fallback`;
- frete: `is_free_shipping`;
- taxonomia: `subniches`;
- auditoria: `source_row_number`, `source_payload`, `created_at`.

O banco preserva `shopType` e `subniches` como arrays. O ranking deriva um
`shop_type_code` pela seguinte prioridade:

```text
1 -> loja oficial
4 -> loja star+
2 -> loja star
```

## catalog_item_import_history

Preserva as linhas imutaveis do modelo antigo por importacao. A migration copia
todo o historico antes de manter em `catalog_items` somente os itens que
pertenciam ao catalogo ativo no momento da conversao.

Essa tabela e apenas de auditoria: nao participa de refresh, score ou ranking e
nao reativa itens de imports antigos.

## offer_selection_state

Mantem estado mutavel separado do snapshot do catalogo.

Campos exigidos pelos contratos de selecao:

- `selected_at`;
- `cooldown_until`;
- `last_sent_at`;
- `selection_count`;
- `selection_reason`;
- `selection_bucket`;
- `similarity_status`;
- `refresh_iteration`;
- `fields_changed`;
- `stability_reached`;
- `rescored_at`;
- `created_at`;
- `updated_at`.

O estado e isolado por `profile + marketplace + stable_key`.

Para `feminino/shopee`, a tabela e a projecao operacional reconstruivel de
`publication_events`:

- somente `confirmed` com `sent_at` participa;
- `selection_count` e `last_sent_at` sao recalculados do ledger;
- `cooldown_until` e meia-noite BRT do terceiro dia apos a publicacao;
- o item fica inelegivel nos dois dias operacionais seguintes;
- similaridade, taxonomia e estado de refresh sao preservados;
- o bloqueio abrange todos os destinos e canais do perfil.

`offers.rebuild_offer_publication_state('feminino', 'shopee')` recompoe a
projecao. O wrapper `scripts/supabase/rebuild_publication_cooldown.py` exige
confirmacao explicita e recusa execucao entre `07h` e `21h`.

## publication_events

Mantem o ledger auditavel de entregas confirmadas pelo worker.

Campos principais:

- `publish_id`;
- `profile`;
- `marketplace`;
- `stable_key`;
- `item_id`;
- `target`;
- `channel_adapter`;
- `delivery_status`;
- `manifest_item_number`;
- `artifact_generated_at`;
- `manifest_created_at`;
- `planned_at`;
- `sent_at`;
- `offer_title`;
- `offer_url`;
- `offer_price`;
- `message_text`;
- `payload`;
- `created_at`;
- `updated_at`.

Regra operacional:

- a linha nasce na confirmacao do worker;
- `publish_id` e o identificador global da publicacao;
- retries do mesmo artifact nao duplicam entrega;
- a unicidade operacional e `profile + target + manifest_item_number + artifact_generated_at`.

O detalhamento de uso e consultas esta em
`docs/supabase-publication-events.md`.

## offer_media_assets

Apos aplicar a migration Instagram, mantem os metadados de midia resolvida para
publicacao Instagram, separado do catalogo comercial. A identidade operacional
e:

```text
profile + marketplace + item_id
```

Campos principais:

- `shop_id`;
- `product_link`, usado como fonte canonica do scrape;
- `image_urls`, lista ordenada de imagens validas;
- `video_url`, primeiro video valido quando existir;
- `source`, inicialmente `shopee_product_html`;
- `status`, com `valid`, `no_media`, `failed` ou `stale`;
- `resolved_at`, `last_checked_at` e `error_detail`.

Essa tabela nao armazena arquivos de imagem ou video. Ela guarda apenas URLs e
metadados validados para que o n8n consuma midia pronta.

## v_instagram_dispatch_ready

Apos aplicar a migration Instagram, sera a superficie de consumo para o workflow
Instagram. A view junta
`offers.v_daily_dispatch_ready` com `offers.offer_media_assets` e expoe somente
itens com:

- slot pronto na fila diaria;
- `offer_media_assets.status = 'valid'`;
- `video_url` para formato `reels`, ou `image_urls` nao vazio para formato
  `carousel`.

A view pode retornar o mesmo item em mais de um formato quando ele tem video e
imagens. Para Instagram, a ordenacao operacional usa `planned_date` e
`daily_sequence`; `planned_hour` permanece apenas como auditoria herdada do
planner. O claim concorrente deve continuar acontecendo sobre
`offers.daily_dispatch_plan`, com `FOR UPDATE SKIP LOCKED`.

O campo `caption_base` inclui descricao com emoji inicial, `offer_link`
afiliado na segunda linha, preco sem "hoje", avaliacao, aviso de
disponibilidade e hashtags. O workflow Instagram pode reconstruir a legenda
final para tratar o `offer_link` como texto copiavel e direcionar o CTA
clicavel para o link do perfil.

## v_offer_ranking_current

A view considera todos os itens do catalogo persistente.

Os dados comerciais sao resolvidos por campo. Quando existe snapshot,
`v_offer_latest_snapshot` fornece o estado mais recente, inclusive quando ele
esta `STALE`; quando nao existe snapshot ou o campo nao veio no payload, o
valor cadastral e usado como fallback. Falhas de refresh nao invalidam
o ultimo snapshot valido.

O frete e a excecao: sem snapshot, preserva o valor do catalogo; com snapshot,
fica desconhecido e recebe zero em `shipping_score`, pois `productOfferV2` nao
retorna esse sinal.

Versao da regra:

```text
commercial_v1
```

Componentes:

| Componente | Regra |
| --- | --- |
| `discount_score` | a partir de 20%, `min(desconto, 40) * 0.5` |
| `commission_score` | comissao maior que zero, `commission_rate * 100` |
| `sales_score` | a partir de 100 vendas, `min(vendas / 100, 20)` |
| `rating_score` | avaliacao a partir de 4.5, 10 pontos |
| `shipping_score` | frete rapido/gratis, 8 pontos |
| `shop_type_score` | tipo 1 = 10, tipo 4 = 7, tipo 2 = 5 |

Comissao Shopee:

```text
sellerCommissionRate + shopeeCommissionRate
```

`commission_rate_fallback` so e usado quando as duas parcelas nao estiverem
disponiveis.

A view tambem entrega:

- `commercial_score`;
- `score_reasons`;
- `discount_percent`;
- `score_version`;
- `is_eligible`;
- `ineligibility_reasons`;
- `rank_profile`;
- `rank_subniche`;
- `commercial_data_source`, com `catalog` ou `snapshot`;
- `refresh_status`, `latest_snapshot_id`, `last_checked_at` e `age_hours`;
- todos os campos de controle da selecao;
- hash e data da primeira importacao do item.

## Elegibilidade

Uma oferta fica elegivel quando:

- `rating >= 4.8`;
- nao esta em cooldown;
- nao foi suprimida por similaridade.

O ranking e calculado apenas para itens elegiveis. Itens bloqueados continuam
visiveis na view, mas recebem ranking nulo e motivo explicito.

Itens em cooldown permanecem visiveis com `cooldown_active`; itens de qualidade
ou similaridade continuam usando seus motivos independentes.

Freshness continua sendo um eixo operacional separado de elegibilidade. Um item
`STALE` pode continuar visivel em `offers.v_offer_ranking_current` para
diagnostico, score e priorizacao de refresh, mas nao deve entrar em
`offers.daily_dispatch_plan` nem ser considerado pronto em
`offers.v_daily_dispatch_ready`.

## Seguranca

- tabelas com RLS habilitado;
- nenhuma policy publica criada;
- `anon` e `authenticated` sem acesso ao schema;
- segredo de conexao apenas no `.env` local;
- nenhuma URL ou senha versionada;
- migration e validadores nunca imprimem a conexao.

## Operacao das migrations

Inspecao somente leitura:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\apply_migrations.py
```

Aplicacao explicita:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\apply_migrations.py `
  --apply `
  --confirm-remote-write APPLY_SUPABASE_MIGRATIONS
```

Validacao do schema e score com rollback:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\validate_catalog_schema.py
```

Validacao local de um catalogo, sem escrita remota:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\import_catalog.py `
  --profile feminino `
  --catalog-file catalogs\clean\feminino\clean_catalog_rating_4_8_plus.csv
```

Importacao incremental explicita:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\import_catalog.py `
  --profile feminino `
  --catalog-file catalogs\clean\feminino\clean_catalog_rating_4_8_plus.csv `
  --observed-at 2026-08-13T10:30:00-03:00 `
  --apply `
  --confirm-remote-write IMPORT_CURATED_CATALOG
```

Saida esperada:

```text
REMOTE_WRITE=OK profile=feminino import_id=<uuid> status=completed operation=created new_items=<n> existing_items=<n> snapshots=<n>
```

O resultado abaixo e historico, anterior ao refactor incremental, e explica a
origem da base que sera convertida. O antigo comando de ativacao nao faz mais
parte da interface atual:

```text
VALIDATION=OK profile=feminino rows=25202 rating=4.80-5.00 subniches=31 sha256=4504ca7a7b62...
REMOTE_WRITE=OK profile=feminino import_id=d94d30be-576b-41a4-a504-cad83e69cec1 status=active operation=created
```

## Uso no MVP

No estado vigente do `feminino`, o n8n nao consome mais diretamente
`offers.v_offer_ranking_current`. O caminho atual e:

```text
offers.v_offer_ranking_current
  -> planner diario so com FRESH
  -> offers.daily_dispatch_plan
  -> offers.v_daily_dispatch_ready revalida FRESH e elegibilidade
  -> n8n
```

O n8n nao deve alterar ranking, score ou elegibilidade. Ele apenas consome a
janela pronta, monta a mensagem e registra o resultado.

A view `offers.v_daily_dispatch_ready` tambem expoe `refresh_status`,
`last_checked_at`, `age_hours` e `latest_snapshot_id` para auditoria da fila.

Para Instagram, o n8n deve consumir `offers.v_instagram_dispatch_ready`, que ja
inclui midia resolvida e validada. O workflow Instagram e separado do workflow
WhatsApp e registra resultados em `offers.publication_events` com
`channel_adapter='instagram_reels'` ou `channel_adapter='instagram_carousel'`.

O consumo direto da view de ranking deve ser lido como contrato legado do MVP
inicial, nao como padrao operacional vigente.

## Proxima etapa

Validar o workflow n8n consultando o catalogo persistente no Supabase para 1 profile,
com envio bloqueado por allowlist e registro em `publication_events`.

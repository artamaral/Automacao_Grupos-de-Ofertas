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
- `catalog_items`;
- `offer_selection_state`;
- `schema_migrations`;
- `v_offer_ranking_current`;
- funcao `activate_catalog_import(uuid)`.

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

Para cada profile, a auditoria confirmou:

- `row_count` declarado igual ao total armazenado;
- total armazenado igual ao total retornado pela view;
- todos os itens elegiveis no momento da carga;
- `rank_profile` continuo, sem lacunas ou duplicacoes;
- hash local igual ao hash registrado no Supabase;
- uma unica importacao ativa por `profile + marketplace`.

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

Registra cada tentativa controlada de publicacao de catalogo.

Controles principais:

- `profile`;
- `marketplace`;
- `source_path`;
- `source_sha256`;
- `source_modified_at`;
- `row_count`;
- `status`;
- `validation_summary`;
- `imported_by`;
- `imported_at`;
- `activated_at`;
- `superseded_at`;
- `rejected_at`;
- `rejection_reason`.

Estados permitidos:

```text
staged -> active -> superseded
staged -> rejected
```

Existe no maximo um catalogo `active` por `profile + marketplace`.

A ativacao deve usar:

```sql
select offers.activate_catalog_import('<import_id>');
```

A funcao substitui atomicamente o catalogo ativo anterior.

## catalog_items

Preserva o snapshot imutavel de cada item pertencente a uma importacao.

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

## v_offer_ranking_current

A view considera apenas itens pertencentes ao catalogo ativo.

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
- todos os campos de controle da selecao;
- hash e data da importacao ativa.

## Elegibilidade

Uma oferta fica elegivel quando:

- `rating >= 4.8`;
- nao esta em cooldown;
- nao foi suprimida por similaridade.

O ranking e calculado apenas para itens elegiveis. Itens bloqueados continuam
visiveis na view, mas recebem ranking nulo e motivo explicito.

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

Importacao e ativacao explicitas:

```powershell
.\.venv\Scripts\python.exe scripts\supabase\import_catalog.py `
  --profile feminino `
  --catalog-file catalogs\clean\feminino\clean_catalog_rating_4_8_plus.csv `
  --apply `
  --activate `
  --confirm-remote-write IMPORT_CURATED_CATALOG
```

## Proxima etapa

Conectar a geracao de mensagens ao catalogo ativo e ao ranking persistido,
mantendo o Cloud Run fora da descoberta local.

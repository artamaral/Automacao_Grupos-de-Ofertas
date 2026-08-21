# Quarentena de itens com erro de nicho

## Status

Definicao operacional aplicada em `2026-08-20` ao catalogo persistente no Supabase.

Profile de quarentena:

```text
erro-nicho
```

O objetivo e retirar do universo operacional de um profile itens que foram
identificados como pertencentes ao nicho errado, sem apagar o registro do
catalogo e sem perder a rastreabilidade do `item_id`.

## Regra

Quando um item do catalogo `feminino` for confirmado como erro de nicho, a
quarentena e feita alterando:

```text
profile = feminino
```

para:

```text
profile = erro-nicho
```

Nao existe hoje um campo dedicado de ativacao/inativacao em
`offers.catalog_items`. O profile `erro-nicho` funciona, portanto, como uma
quarentena logica do catalogo persistente.

Essa mudanca nao apaga o item. Ela preserva `item_id`, dados cadastrais,
`source_payload` e demais campos existentes em `offers.catalog_items`.

## Efeito operacional

A separacao funciona porque `offers.v_offer_refresh_status` recebe `profile`
diretamente de `offers.catalog_items` e depende de uma policy correspondente em
`offers.candidate_refresh_policies`.

No estado validado em `2026-08-20` existe policy operacional para:

```text
profile = feminino
marketplace = shopee
ttl_hours = 24
```

Nao existe policy para `erro-nicho`.

Consequentemente, um item movido de `feminino` para `erro-nicho`:

1. deixa de pertencer ao conjunto `feminino` em `offers.catalog_items`;
2. deixa de aparecer em `offers.v_offer_refresh_status` como `feminino`;
3. deixa de aparecer em `offers.v_offer_ranking_current` como `feminino`;
4. deixa de ser candidato para a fila operacional feminina;
5. permanece armazenado no catalogo para auditoria e eventual revisao futura.

Alterar somente `subniches` nao oferece a mesma garantia. A quarentena definida
neste documento depende da alteracao de `profile`.

## Primeira aplicacao

Em `2026-08-20`, uma auditoria dos `negative_terms` do profile `feminino`
identificou `2.285` `item_id` unicos candidatos a retirada do nicho.

Os IDs auditados foram atualizados explicitamente no Supabase de:

```text
feminino -> erro-nicho
```

A operacao usou a lista fechada dos `2.285` `item_id`, sem recalcular a regra de
matching durante o `UPDATE`.

## Validacao no Supabase

Apos a alteracao, foram executadas consultas de validacao diretamente no
Supabase. Resultado observado em `2026-08-20`:

| Verificacao | Resultado |
| --- | ---: |
| `item_id` em `offers.catalog_items` com `profile = 'erro-nicho'` | 2.285 |
| linhas fisicas correspondentes em `erro-nicho` | 2.285 |
| IDs da quarentena ainda em `catalog_items` como `feminino` | 0 |
| IDs da quarentena ainda em `v_offer_refresh_status` como `feminino` | 0 |
| IDs da quarentena ainda em `v_offer_ranking_current` como `feminino` | 0 |
| itens restantes no catalogo `feminino` | 28.077 |

A validacao cruzada confirmou explicitamente:

```text
quarantined_ids = 2285
still_catalog_feminino = 0
still_refresh_feminino = 0
still_ranking_feminino = 0
```

Portanto, para o desenho operacional vigente, a alteracao de `profile` para
`erro-nicho` garante que esses itens nao sejam mais considerados pelo fluxo de
refresh, ranking e montagem da fila do profile `feminino`.

## Limpezas adicionais em 2026-08-21

### Auditoria pelo snapshot mais recente

A auditoria inicial dos `2.285` itens usou o `product_name` persistido em
`offers.catalog_items`. Foi identificado que o fluxo operacional pode usar o
`product_name` mais recente de `offers.offer_snapshots`, que pode divergir do
nome cadastral original para o mesmo `item_id`.

Por isso foi executada uma nova verificacao dos `negative_terms` contra o
snapshot mais recente de cada item ainda no profile `feminino`.

Foram encontrados `11` itens. Quatro deles tinham somente o termo `adulto` e
foram mantidos no profile `feminino`, por serem produtos femininos validos no
contexto observado.

Os outros `7` itens foram movidos para `erro-nicho`:

```text
18197643923
20997632799
23292865377
23299150359
23493236809
42075927843
58200460933
```

A validacao apos o `UPDATE` confirmou:

```text
moved_to_erro_nicho = 7
still_feminino = 0
```

### Limpeza manual por descricao

Na sequencia, foram localizados no catalogo e no snapshot atual itens que nao
pertencem ao universo de publicacao dos profiles operacionais atuais. Foram
movidos explicitamente para `erro-nicho` os seguintes `21` `item_id`:

```text
13111824947
19808697032
20997924526
22294564575
22299196951
22398027085
22994507281
23099427373
23193203772
23198346659
23598472024
23997887366
28644078356
43074113593
44757996163
47756408151
48951679594
51956451693
58208389522
58254357436
58254584392
```

Esse conjunto inclui:

- meia tematica de pe de frango/galinha/galo;
- escudo decorativo do Santa Cruz;
- conjuntos infantis de 1 a 16 anos;
- gelatinas capilares com denominacao `Kids`;
- camisetas Brasil/unissex identificadas na revisao;
- trofeus e objetos decorativos de kimono/jiu-jitsu/judo/karate;
- saia metalizada de Carnaval identificada na revisao manual.

Um dos `21` itens estava em `mae-e-bebe`; os demais estavam em `feminino`. A
operacao foi feita por lista fechada de `item_id`, sem matching dinamico no
momento do `UPDATE`.

A validacao apos essa limpeza confirmou:

```text
target_item_ids = 21
in_erro_nicho = 21
still_other_profile = 0
missing_from_catalog = 0
```

### Estado consolidado apos as limpezas

Consulta direta ao Supabase em `2026-08-21` confirmou:

| Profile | Linhas | `item_id` unicos |
| --- | ---: | ---: |
| `erro-nicho` | 2.313 | 2.313 |
| `feminino` | 28.050 | 28.050 |
| `mae-e-bebe` | 11.696 | 11.696 |

O total de `2.313` em `erro-nicho` corresponde a:

```text
2.285 da primeira auditoria
+ 7 da auditoria por snapshot
+ 21 da limpeza manual
= 2.313 item_id unicos
```

## Uso futuro

`erro-nicho` deve ser tratado como profile de quarentena, nao como novo nicho de
publicacao.

Nao adicionar uma entrada para `erro-nicho` em
`offers.candidate_refresh_policies` nem uma politica de selecao/publicacao sem
uma decisao explicita de reativacao desse universo.

Uma eventual restauracao deve ser deliberada e alterar o item para o profile
correto somente depois da revisao de nicho/taxonomia.

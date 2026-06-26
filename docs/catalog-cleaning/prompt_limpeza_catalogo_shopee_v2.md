# Prompt operacional determinístico — Limpeza e transformação de catálogo Shopee

## Objetivo fechado

Transformar um arquivo CSV de catálogo de produtos Shopee em arquivos limpos, auditáveis e prontos para uso em automação de ofertas, sem criação livre de regras, subcategorias, nomes de colunas ou critérios de decisão.

O processo deve obrigatoriamente:

1. Ler o CSV de entrada.
2. Remover produtos inválidos conforme critérios fixos.
3. Remover duplicatas seguras por `shopId + itemId`.
4. Marcar, sem remover, candidatos a duplicata por `productName + price`.
5. Popular `subniches` usando obrigatoriamente o arquivo-base `shopee_subniches_taxonomia_base.json`; usar `source_hits` e, apenas quando a taxonomia permitir, `productName`.
6. Gerar arquivos de saída com auditoria.
7. Gerar resumo de execução com contagens.
8. Falhar quando o arquivo não permitir cumprir o contrato mínimo.

Não é permitido inventar regras adicionais, criar subnichos novos, alterar o nome das colunas de saída, remover linhas fora dos critérios definidos ou consultar fontes externas. Novas palavras-chave só podem ser associadas a subnichos existentes quando forem registradas no arquivo-base de taxonomia; a execução da limpeza não deve criar mapeamentos temporários.

---

## Arquivo de entrada esperado

Entrada obrigatória:

```text
clean_catalog.csv
```

Arquivo-base obrigatório para subnichos:

```text
shopee_subniches_taxonomia_base.json
```

Este arquivo é a fonte oficial de verdade para a coluna `subniches`. Se ele estiver ausente, inválido ou contiver `source_keyword_to_subniche` apontando para um valor fora de `allowed_subniches`, interromper o processo e reportar erro. Não usar a taxonomia embutida no prompt como substituta quando o arquivo-base existir.

Formato obrigatório:

```text
CSV com cabeçalho na primeira linha, codificação UTF-8 ou compatível com leitura por pandas.read_csv.
```

Colunas mínimas obrigatórias:

```text
itemId
shopId
productName
productLink
offerLink
imageUrl
commission
price
sales
ratingStar
priceDiscountRate
source_hits
```

Se qualquer uma dessas colunas estiver ausente, interromper o processo e reportar erro. Não tentar inferir coluna equivalente.

---

## Regras de limpeza obrigatórias

### 1. Preservação de rastreabilidade

Antes de qualquer filtro, criar:

```text
_source_row
```

Regra:

```text
_source_row = número da linha original no CSV, considerando cabeçalho na linha 1.
```

Exemplo: primeira linha de dados = `_source_row = 2`.

---

### 2. Validação de imagem

Coluna usada:

```text
imageUrl
```

Manter somente linhas em que `imageUrl`:

```text
não esteja vazia
não seja nan, none, null ou []
comece com http:// ou https://
```

Remover caso contrário.

Motivo de remoção:

```text
imagem_faltando_ou_invalida
```

Não abrir a URL. Não baixar imagem. Não validar disponibilidade remota.

---

### 3. Validação de preço

Coluna usada:

```text
price
```

Converter para número.

Manter somente linhas em que:

```text
price > 0
```

Remover caso `price` esteja vazio, inválido, não numérico ou menor/igual a zero.

Motivo de remoção:

```text
preco_faltando_ou_invalido
```

---

### 4. Validação de comissão

Coluna usada:

```text
commission
```

Converter para número.

Manter somente linhas em que:

```text
commission > 0
```

Remover caso `commission` esteja vazia, inválida, não numérica ou menor/igual a zero.

Motivo de remoção:

```text
comissao_faltando_ou_invalida
```

---

### 5. Validação de nota

Coluna usada:

```text
ratingStar
```

Converter para número.

Manter somente linhas em que:

```text
ratingStar >= 4.5
```

Remover caso `ratingStar` esteja vazia, inválida ou menor que `4.5`.

Motivo de remoção:

```text
nota_menor_que_4_5_ou_invalida
```

Produto com nota `0`, mesmo que seja novo, deve ser removido.

---

### 6. Validação de IDs Shopee

Colunas usadas:

```text
shopId
itemId
```

Manter somente linhas em que ambas estejam preenchidas.

Remover caso uma delas esteja vazia.

Motivo de remoção:

```text
shopId_ou_itemId_faltando
```

---

## Deduplicação segura obrigatória

### Chave segura

Criar:

```text
_dedupe_key = shopId + ':' + itemId
```

Remover duplicatas apenas quando `_dedupe_key` se repetir.

### Critério de escolha da linha mantida

Quando houver duplicatas por `_dedupe_key`, manter a melhor linha usando esta ordenação fixa:

1. Maior `commission`.
2. Maior `ratingStar`.
3. Maior `sales`.
4. Maior `priceDiscountRate`.
5. Menor `_source_row`.

As demais linhas com o mesmo `_dedupe_key` devem ir para o arquivo de removidos com motivo:

```text
duplicata_exata_shopId_itemId
```

Adicionar ao catálogo limpo:

```text
_dedupe_key
_duplicate_count
_quality_rank
```

Regra de `_quality_rank`:

```text
1 para a melhor linha após ordenação de qualidade, 2 para a segunda, e assim por diante.
```

---

## Duplicatas heurísticas por nome + preço

Estas linhas não devem ser removidas automaticamente.

### Regra de grupo

Criar chave temporária:

```text
name_price_key = normalizar(productName) + '|' + price literal
```

Normalização de `productName`:

```text
converter para minúsculas
remover espaços nas pontas
colapsar múltiplos espaços internos para um único espaço
não remover acentos
não remover pontuação
```

### Regra de marcação

Para cada grupo com mais de uma linha:

1. A primeira linha pela ordem atual do catálogo limpo é a linha keeper.
2. Todas as demais linhas do grupo devem ser marcadas como candidatas.
3. Não remover essas linhas do catálogo limpo.

Adicionar colunas:

```text
duplicate_name_price_tag
duplicate_name_price_group_id
duplicate_name_price_group_size
duplicate_name_price_keeper
```

Valores obrigatórios:

```text
duplicate_name_price_tag = candidato_revisao_duplicata_nome_preco
```

Somente nas linhas candidatas.

```text
duplicate_name_price_keeper = true
```

Na primeira linha do grupo.

```text
duplicate_name_price_keeper = false
```

Nas demais linhas do grupo.

Para linhas fora de grupos duplicados, deixar as colunas vazias.

No arquivo histórico usado neste projeto, esta regra identificou:

```text
624 grupos por productName + price
1.538 linhas envolvidas
914 candidatas marcadas
```

---

## Regras obrigatórias para `subniches`

A coluna `subniches` deve ser sobrescrita. Não preservar valor antigo como fonte de verdade.

Formato obrigatório da coluna:

```text
JSON array string
```

Exemplo:

```json
["alimentacao-mamadeiras"]
```

Quando houver mais de um subniche aplicável via `source_hits`, manter todos, sem duplicar, na ordem em que aparecem nos hits normalizados.

Exemplo:

```json
["roupas-geral", "roupas-body", "roupas-macacao"]
```

Adicionar também:

```text
subniche_basis
source_keywords_norm
unmapped_source_keywords
```

---

## Parsing obrigatório de `source_hits`

`source_hits` deve ser interpretado como JSON array quando possível.

Exemplos válidos:

```json
["keyword:carrinho bebê"]
["matchId:100632", "keyword:bebê"]
```

Normalização:

```text
converter para minúsculas
remover espaços nas pontas
se começar com keyword:, remover o prefixo keyword:
se começar com matchId:, manter como matchid:<id> em minúsculas
```

Salvar a lista normalizada em:

```text
source_keywords_norm
```

Formato obrigatório:

```text
JSON array string
```

---

## Taxonomia fechada via arquivo-base obrigatório

Usar obrigatoriamente o arquivo:

```text
shopee_subniches_taxonomia_base.json
```

O arquivo deve conter, no mínimo:

```text
allowed_subniches
source_keyword_to_subniche
generic_source_hits
generic_default_subniche
fallback_product_name_rules
```

### Regra de autoridade

`shopee_subniches_taxonomia_base.json` é a fonte de verdade. A lista legível em `shopee_subniches_palavras_chave.csv` pode ser usada para auditoria humana, mas a execução deve usar o JSON.

### Validação obrigatória da taxonomia

Antes de classificar qualquer produto, validar:

```text
1. allowed_subniches existe e não está vazio.
2. source_keyword_to_subniche existe.
3. Todo valor de source_keyword_to_subniche pertence a allowed_subniches.
4. generic_default_subniche pertence a allowed_subniches.
5. Todo subniche em fallback_product_name_rules pertence a allowed_subniches.
6. Não há subniche vazio.
7. Não há palavra-chave vazia.
```

Se qualquer validação falhar, interromper o processo.

### Lista fechada de subnichos permitidos nesta versão

```text
alimentacao-aquecedores
alimentacao-babadores
alimentacao-cadeiras
alimentacao-copos-treinamento
alimentacao-esterilizadores
alimentacao-mamadeiras
alimentacao-pratos-talheres
amamentacao-almofadas
amamentacao-armazenamento-leite
amamentacao-extracao-leite
banho-banheiras
bebe-geral
brinquedos-e-desenvolvimento
brinquedos-montessori
brinquedos-tapetes-atividade
desfralde
enxoval-kits
festas-lembrancinhas
higiene-saude-aspiradores-nasais
higiene-saude-cuidados
higiene-saude-termometros
higiene-saude-unhas
maternidade-bolsas-mochilas
oral-mordedores-chupetas
passeio-bebe-conforto
passeio-canguru-ergonomico
passeio-carrinhos
passeio-sling-wrap
quarto-monitoramento
quarto-organizacao-berco
quarto-sono
quarto-sono-mosquiteiros
roupas-body
roupas-geral
roupas-macacao
seguranca-infantil
troca-fraldas-descartaveis
troca-fraldas-reutilizaveis
troca-trocadores-portateis
```

### Atualização de palavras-chave

É permitido adicionar novas palavras-chave ao arquivo-base somente desta forma:

```text
1. A nova palavra-chave deve ser normalizada.
2. A nova palavra-chave deve apontar para um subniche já existente em allowed_subniches.
3. Não é permitido adicionar novo subniche.
4. Não é permitido criar mapeamento temporário durante a limpeza.
5. Se a palavra-chave ainda não estiver no arquivo-base, registrar em unmapped_source_keywords no resumo e classificar conforme as regras de fallback/default.
```

Em outras palavras: a execução usa apenas o que já está no arquivo-base. A expansão de palavras-chave é uma atualização explícita da taxonomia, não uma decisão criativa durante a limpeza.

---

## Tratamento de `source_hits` genérico

São considerados genéricos somente os valores listados em `generic_source_hits` no arquivo-base `shopee_subniches_taxonomia_base.json`.

Para esta versão histórica, os valores são:

```text
bebê
bebe
matchid:100632
```

Se `source_hits` contiver somente termos genéricos ou estiver vazio, usar `productName` apenas com as regras fechadas de `fallback_product_name_rules` do arquivo-base.

Se nenhuma regra fechada casar, usar obrigatoriamente:

```json
["bebe-geral"]
```

Não inventar categoria.

### Regras fechadas de fallback por `productName`

Aplicar somente as regras existentes em `fallback_product_name_rules` no arquivo-base `shopee_subniches_taxonomia_base.json`, respeitando o campo `order`. A primeira regra que casar vence.

Não criar padrão novo durante a limpeza. Para adicionar novo padrão, atualizar antes o arquivo-base, sempre apontando para um subniche já existente.

Valor de `subniche_basis`:

```text
source_hits
```

Quando pelo menos um `source_hit` específico da taxonomia foi usado.

```text
source_hits_generico+productName
```

Quando `source_hits` era genérico e a classificação veio do `productName`.

```text
source_hits_generico
```

Quando `source_hits` era genérico e o fallback final foi `bebe-geral`.

```text
sem_regra_taxonomia
```

Quando havia `source_hits`, mas nenhum termo pertence à taxonomia e nenhuma regra de fallback casou.

---

## Arquivos de saída obrigatórios

Gerar estes arquivos:

```text
shopee_catalogo_limpo_subniches.csv
shopee_catalogo_removidos.csv
shopee_catalogo_duplicados_914.csv
shopee_catalogo_subniches_resumo.json
```

### `shopee_catalogo_limpo_subniches.csv`

Deve conter somente produtos aprovados pelos filtros de qualidade e deduplicação segura.

Deve conter, no mínimo, as colunas originais e as colunas adicionais:

```text
_quality_rank
_source_row
_dedupe_key
_duplicate_count
duplicate_name_price_tag
duplicate_name_price_group_id
duplicate_name_price_group_size
duplicate_name_price_keeper
subniches
subniche_basis
source_keywords_norm
unmapped_source_keywords
```

### `shopee_catalogo_removidos.csv`

Deve conter todos os produtos removidos e a coluna:

```text
removal_reason
```

Se uma linha tiver mais de um motivo, separar por `|`.

Exemplo:

```text
preco_faltando_ou_invalido|nota_menor_que_4_5_ou_invalida
```

### `shopee_catalogo_duplicados_914.csv`

Deve conter somente linhas em que:

```text
duplicate_name_price_tag = candidato_revisao_duplicata_nome_preco
```

Não incluir os keepers neste arquivo.

### `shopee_catalogo_subniches_resumo.json`

Deve conter:

```text
generated_at
input_file
output_files
original_rows
removed_quality_rows
removed_safe_duplicate_rows
clean_rows
duplicate_name_price_rule
duplicate_name_price_groups
duplicate_name_price_rows_in_groups
duplicate_name_price_candidates_tagged
subniche_counts
subniche_basis_counts
quality_filter_counts
taxonomy_file
taxonomy_version
taxonomy
unmapped_source_keywords
```

---

## Validações obrigatórias para o arquivo histórico deste projeto

Quando a entrada for o arquivo histórico `clean_catalog.csv`, o resultado esperado é:

```text
original_rows = 48844
removed_quality_rows = 23255
removed_safe_duplicate_rows = 0
clean_rows = 25589
duplicate_name_price_groups = 624
duplicate_name_price_rows_in_groups = 1538
duplicate_name_price_candidates_tagged = 914
```

Se esses números não baterem, reportar divergência e não afirmar sucesso total.

---

## Restrições e riscos do arquivo que podem impedir o objetivo

1. Se `shopId` ou `itemId` estiverem ausentes, não é possível fazer deduplicação segura por ID real do produto.
2. Se `source_hits` estiver vazio, malformado, genérico demais ou contiver palavra-chave fora do arquivo-base, a classificação de `subniches` fica limitada ao fallback/default permitido pela taxonomia.
3. Se `productName` for genérico, incompleto ou poluído com palavras irrelevantes, o fallback pode cair em `bebe-geral`.
4. Se `price` ou `commission` vierem em formato textual inconsistente, a conversão numérica pode falhar e a linha deve ser removida.
5. Se `ratingStar` vier zerado para produto novo, o produto será removido mesmo que possa ser uma boa oferta, porque a regra fixa exige nota mínima `4.5`.
6. Se `imageUrl` existir mas a imagem estiver fora do ar, o processo não detecta, porque não deve abrir URLs.
7. Duplicata por `productName + price` é heurística; por isso deve ser marcada, não removida.
8. Produtos iguais vendidos por lojas diferentes podem aparecer nos 914 candidatos e devem passar por revisão humana ou regra de negócio posterior.
9. A taxonomia-base `shopee_subniches_taxonomia_base.json` é específica para o catálogo `Mãe e Bebê`; para outro nicho, não adaptar criativamente. Criar outro arquivo-base de taxonomia antes de executar.
10. Se a Shopee mudar o significado de comissão, preço, nota ou IDs, o arquivo pode não representar o estado atual do marketplace.
11. Se houver múltiplas linhas do mesmo produto com valores diferentes de comissão ou preço, a regra mantém a linha de maior qualidade definida neste prompt, não necessariamente a mais recente.
12. Não há validação de link de afiliado; `offerLink` é preservado como veio no arquivo.

---

## Harness obrigatório

Executar com Python 3.10+.

Instalar dependência, se necessário:

```bash
pip install pandas
```

Comando para reproduzir o processamento histórico:

```bash
python catalog_cleaning_harness_v2.py \
  --input clean_catalog.csv \
  --taxonomy-file shopee_subniches_taxonomia_base.json \
  --outdir ./out_catalogo_shopee \
  --expected-input-rows 48844 \
  --expected-clean-rows 25589 \
  --expected-duplicate-candidates 914
```

Critérios de sucesso do harness:

```text
1. O script termina sem erro.
2. O resumo JSON é criado.
3. O CSV limpo contém 25.589 linhas para o arquivo histórico.
4. O CSV de candidatos contém 914 linhas para o arquivo histórico.
5. Nenhum subniche fora de `allowed_subniches` do arquivo-base é criado.
6. Nenhuma linha candidata por productName + price é removida automaticamente.
```

Critérios de falha:

```text
1. Coluna obrigatória ausente.
2. Divergência nas contagens esperadas quando parâmetros --expected-* forem usados.
3. Erro de leitura do CSV.
4. Falha ao escrever os arquivos de saída.
```

---

## Proibições explícitas

Não fazer:

```text
não criar subniche novo
não associar palavra-chave nova sem atualizar o arquivo-base antes
não renomear colunas
não remover os 914 candidatos por productName + price
não usar IA para decidir categoria fora da tabela
não consultar internet
não baixar imagens
não abrir links Shopee
não recalcular comissão
não alterar offerLink
não usar productName quando source_hits específico já definiu o subniche
não classificar produto ambíguo fora das regras fechadas
não afirmar sucesso se as validações não baterem
```

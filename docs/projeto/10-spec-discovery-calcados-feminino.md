# 10 - Spec de Discovery Cirurgico de Calcados Feminino

## Status

Proposta revisada, pronta para implementacao.

## Objetivo

Adicionar uma capacidade **isolada, cirurgica e aditiva** para rodar discovery de calcados dentro do profile operacional `feminino`, sem criar um profile tecnico paralelo.

A nova capacidade deve permitir executar o builder atual com um escopo declarativo:

```bash
shopee-catalog-builder --profile feminino --discovery-scope <scope>
```

Nesta entrega, o primeiro novo escopo implementado e:

```bash
shopee-catalog-builder --profile feminino --discovery-scope calcado
```

Quando `--discovery-scope calcado` for usado:

- o profile operacional continua sendo `feminino`;
- a coleta usa somente as keywords aprovadas de calcados;
- a saida permanece compativel com importacao posterior como `profile=feminino`;
- nenhum item deve nascer como profile operacional `feminino-calcados`.

Quando a flag nao for usada, o comportamento atual de `--profile feminino` deve permanecer exatamente igual.

## Principio obrigatorio: regressao zero

Tudo que ja existe deve permanecer intacto.

Esta implementacao **nao pode alterar**:

- as `keyword_terms` atuais do profile `feminino`;
- os grupos macro atuais do profile `feminino`;
- discovery dos demais nichos;
- provider Shopee;
- algoritmo de coleta;
- paginacao;
- deduplicacao;
- filtros negativos existentes;
- classificacao atual de itens ja existentes;
- score comercial;
- cooldown;
- fallback;
- selecao editorial;
- regras de rotacao;
- horarios;
- publicacao;
- Supabase;
- n8n;
- WhatsApp;
- WAHA;
- contratos downstream.

A mudanca deve ser declarativa sempre que possivel. Nao fazer refatoracoes oportunistas, limpeza de codigo, reorganizacao de profiles ou qualquer mudanca nao necessaria para suportar `--discovery-scope calcado`.

## Contexto tecnico confirmado

O builder atual recebe `--profile`, carrega `config/shopee_catalog_profiles.toml` e executa uma coleta `productOfferV2(keyword=...)` para cada termo configurado em `keyword_terms`.

O problema de criar um profile tecnico `feminino-calcados` e que a saida nasce com `catalog_profile_slug=feminino-calcados`, o que exige normalizacao/remendo antes de importar para o catalogo operacional `feminino`.

Como a necessidade real e descobrir calcados **para o profile feminino**, a identidade operacional deve continuar sendo:

```text
profile = feminino
marketplace = shopee
```

Portanto, a feature correta e um escopo de discovery dentro do profile existente, nao um novo profile.

## Nova capacidade permitida

Adicionar uma flag opcional ao builder:

```text
--discovery-scope <scope>
```

Regras:

- a flag so deve restringir as fontes de coleta;
- a flag deve aceitar somente grupos macro declarados em `profile.subniches[].slug`;
- a flag nao muda `profile.slug`;
- a flag nao muda `catalog_profile_slug` na saida;
- a flag nao cria novo destino operacional;
- a flag nao cria novo grupo;
- a flag nao cria nova regra editorial;
- a flag nao altera filtros, dedup, score, fallback, cooldown ou publicacao.

Se a flag nao for informada, `shopee-catalog-builder --profile feminino` deve usar as `keyword_terms` atuais do profile `feminino`, sem diferenca de comportamento.

## Generalizacao obrigatoria para grupos macro

A implementacao da flag nao deve ser hardcoded para calcados.

O contrato esperado e generico:

```bash
shopee-catalog-builder --profile <profile> --discovery-scope <scope>
```

Onde:

- `<profile>` e o profile operacional existente, por exemplo `feminino`;
- `<scope>` deve ser um grupo macro declarado em `subniches` do profile carregado;
- cada grupo macro existente em `profile.subniches[].slug` deve ficar automaticamente habilitado como valor valido da flag;
- quando um novo grupo macro for adicionado a `profile.subniches`, ele deve ficar automaticamente habilitado para uso na flag;
- as keywords do scope devem vir de `profile.subniches[].keyword_terms`;
- grupos macro podem apontar para um ou mais subnichos editoriais permitidos na taxonomia por meio de `target_subniches`;
- a execucao focada usa somente as `keyword_terms` do escopo escolhido;
- a saida continua mantendo a identidade operacional do profile original.

Portanto, o mesmo mecanismo deve permitir imediatamente algo como:

```bash
shopee-catalog-builder --profile feminino --discovery-scope moda
shopee-catalog-builder --profile feminino --discovery-scope cabelo
shopee-catalog-builder --profile feminino --discovery-scope calcado
```

desde que esses slugs existam em `subniches` do profile `feminino`.

Nesta entrega, o grupo macro `calcado` tambem deve existir para permitir uma unica rodada focada em toda a familia de calcados, sem exigir rodadas separadas para `calcados-sandalia`, `calcados-sapatilha`, `calcados-chinelo`, `calcados-rasteirinha` e `calcados-mocassim`.

Se um usuario informar um escopo que nao exista em `profile.subniches[].slug`, o builder deve falhar de forma explicita, antes de chamar o provider.

## Fonte canonica dos scopes permitidos

A flag deve ser amarrada aos grupos macro ja declarados no profile, para impedir scopes soltos e para evitar chamadas excessivamente fragmentadas por subnicho editorial fino.

Para `feminino`, a fonte canonica dos scopes permitidos e:

```text
config/shopee_catalog_profiles.toml
```

Campo obrigatorio:

```text
profiles[].subniches[].slug
```

Exemplos de scopes validos esperados para o profile `feminino`:

```text
moda
cabelo
calcado
maquiagem
skincare
unhas
acessorios
```

`calcado` e o novo grupo macro desta entrega. Os demais ja existem no profile atual e devem funcionar com a mesma flag sem cadastro paralelo.

Os subnichos editoriais finos da taxonomia continuam existindo, mas nao devem ser a interface principal da flag. Portanto, comandos como estes nao devem ser o caminho recomendado:

```bash
shopee-catalog-builder --profile feminino --discovery-scope moda-vestidos
shopee-catalog-builder --profile feminino --discovery-scope cabelo-tratamento
```

Esses slugs finos podem continuar sendo usados pela classificacao/limpeza/editorial, mas a descoberta operacional focada deve acontecer pelo grupo macro.

## Validacao contra a taxonomia editorial

Para `feminino`, a fonte canonica de subnichos permitidos e:

```text
config/catalog-taxonomies/feminino/shopee_feminino_subniches_taxonomia_base.json
```

Campo obrigatorio:

```text
allowed_subniches
```

Regras:

- `allowed_subniches` nao define diretamente os valores da flag;
- `allowed_subniches` deve ser usado para validar `target_subniches` de cada grupo macro quando o grupo declarar esse campo;
- todo item em `target_subniches` deve existir em `allowed_subniches`;
- se qualquer `target_subniche` nao existir na taxonomia vigente, o builder deve falhar antes de chamar o provider;
- a validacao deve acontecer no carregamento/planejamento da execucao, nao depois da coleta;
- nao criar uma segunda lista manual de subnichos editoriais atuais dentro do discovery.

Exemplo de grupo macro existente:

```bash
shopee-catalog-builder --profile feminino --discovery-scope cabelo
```

Nesse caso, `cabelo` precisa existir em `profile.subniches[].slug`, e as keywords devem vir do proprio bloco `subniches` do profile.

Para o novo grupo macro de calcados, declarar um novo item no array `subniches` existente:

```toml
{ slug = "calcado", name = "Calcados Femininos", target_subniches = ["calcados-sandalia", "calcados-sapatilha", "calcados-chinelo", "calcados-rasteirinha", "calcados-mocassim"], keyword_terms = [...], negative_terms = [...] }
```

Assim, a capacidade atende o caso operacional correto:

- discovery focado em grupos macro, para reduzir quantidade de chamadas;
- classificacao e planejamento continuam trabalhando com subnichos editoriais finos.

## Keywords de discovery

Usar somente termos simples, sem obrigar a palavra `feminino` na query.

Conjunto aprovado para o escopo `calcado`:

```text
sandalia
sapatilha
chinelo
rasteirinha
rasteira
mocassim
loafer
papete
tamanco
slide
birken
```

### Justificativa

A adicao de `feminino` as queries, como `chinelo feminino`, reduz o recall e pode deixar de recuperar produtos validos cujo titulo contenha apenas `chinelo`, `slide`, `papete` etc.

O discovery deve privilegiar recall e deixar a contencao de resultados inadequados para as mesmas travas negativas ja usadas no universo feminino.

## Validacao com amostra real

Foi analisado o arquivo:

```text
BatchProductLinks20260825161442-ad1b1e5c698c47b49c14c5de292bd968.csv
```

A amostra contem **67 itens**.

Aplicando correspondencia textual normalizada sobre `Item Name`, o conjunto aprovado de 11 termos simples cobriu:

```text
67 / 67 itens = 100% da amostra
```

Cobertura observada por termo na amostra:

| Keyword | Itens com correspondencia |
|---|---:|
| `sandalia` | 32 |
| `sapatilha` | 13 |
| `tamanco` | 11 |
| `chinelo` | 10 |
| `papete` | 6 |
| `rasteirinha` | 5 |
| `slide` | 5 |
| `rasteira` | 3 |
| `birken` | 3 |
| `mocassim` | 2 |
| `loafer` | 2 |

Ha sobreposicao entre keywords; isso e esperado e deve continuar sendo tratado pela deduplicacao ja existente.

A cobertura de 100% vale para esta amostra e **nao deve ser interpretada como garantia universal de cobertura de todo o catalogo da Shopee**.

## Feminino sem forcar `feminino` na keyword

Nao adicionar `feminino` as queries de discovery apenas para reforcar o genero.

O escopo `calcado` deve continuar usando as travas negativas vigentes do profile `feminino`, incluindo termos como:

```text
masculino
masculin
for men
for man
```

alem das demais exclusoes ja existentes e aplicaveis.

Nao modificar os `negative_terms` do profile `feminino` nesta entrega.

## Relacao entre keywords e subnichos

Keyword de discovery nao e equivalente a subnicho editorial.

Termos como:

```text
papete
tamanco
slide
birken
```

podem ser usados para descobrir produtos sem criar subnichos com esses nomes.

Os subnichos finais aprovados para a expansao de calcados continuam sendo:

```text
calcados-sandalia
calcados-sapatilha
calcados-chinelo
calcados-rasteirinha
calcados-mocassim
```

Esta spec cobre somente a selecao focada de keywords durante o discovery. Ela nao cria subnichos novos alem dos ja aprovados na etapa de taxonomia/planejamento.

## Configuracao esperada

Adicionar a configuracao declarativa do grupo macro dentro do bloco existente `slug = "feminino"` em:

```text
config/shopee_catalog_profiles.toml
```

Formato recomendado: adicionar somente este item ao array `subniches = [` ja existente no bloco `slug = "feminino"`:

```toml
{ slug = "calcado", name = "Calcados Femininos", target_subniches = ["calcados-sandalia", "calcados-sapatilha", "calcados-chinelo", "calcados-rasteirinha", "calcados-mocassim"], keyword_terms = ["sandalia", "sapatilha", "chinelo", "rasteirinha", "rasteira", "mocassim", "loafer", "papete", "tamanco", "slide", "birken"], negative_terms = ["masculino", "masculina", "masculinos", "masculinas", "masculin", "for men", "for man"] },
```

Regras:

- nao alterar a lista atual de `keyword_terms` do profile `feminino`;
- nao criar `[[profiles]] slug = "feminino-calcados"`;
- nao criar heranca/refatoracao de `negative_terms`;
- nao modificar profiles de outros nichos;
- nao alterar os itens atuais do array `subniches`; apenas adicionar o novo item `calcado`;
- nao criar `discovery_scopes` separado se `subniches` ja representa os grupos macro do profile;
- o suporte no loader/CLI deve ser generico para qualquer `profile.subniches[].slug`;
- o loader/CLI deve validar `target_subniches` contra `allowed_subniches` da taxonomia do profile quando o campo existir.

## Execucao esperada

Discovery completo atual:

```bash
shopee-catalog-builder --profile feminino
```

Discovery focado em calcados:

```bash
shopee-catalog-builder --profile feminino --discovery-scope calcado
```

Nao criar flags como:

```text
--feminino-calcados
--calcados
--only-keywords
```

Nao criar novo CLI, novo collector, novo provider ou novo metodo de acesso a Shopee.

## Identidade operacional e importacao

O escopo `calcado` e apenas um filtro de discovery.

Mesmo quando `--discovery-scope calcado` for usado, a saida deve continuar representando:

```text
catalog_profile_slug = feminino
catalog_profile_name = Feminino
```

Qualquer importacao futura para Supabase deve usar:

```text
profile = feminino
marketplace = shopee
```

E nunca:

```text
profile = feminino-calcados
```

Esta spec nao executa a importacao remota. Ela apenas garante que o artefato gerado pelo discovery focado ja nasce com a identidade correta para importacao controlada posterior como `feminino`.

## Isolamento de saida

A rodada focada deve ter isolamento proprio para nao sobrescrever uma rodada completa do profile.

Formato recomendado:

```text
.data/shopee_catalog/feminino/scopes/calcado/<run-id>/
```

Tambem e aceitavel outro formato equivalente, desde que:

- preserve `catalog_profile_slug=feminino` nos artefatos;
- nao sobrescreva `.data/shopee_catalog/feminino/<run-id>/` de rodadas completas;
- deixe claro no `run_summary.json` que `discovery_scope=calcado`;
- seja testavel sem chamada real a Shopee.

## Fora de escopo

Esta entrega nao deve:

- importar automaticamente o resultado no Supabase;
- promover itens para producao;
- alterar `catalog_items` remotamente;
- alterar score;
- alterar cooldown;
- alterar fallback;
- alterar selecao editorial;
- alterar horarios;
- alterar n8n;
- alterar WhatsApp;
- alterar WAHA;
- criar novo grupo;
- criar novo destino operacional;
- criar novo profile operacional;
- criar regra de rotacao;
- criar regra especifica de escolha por horario.

## Criterios de aceitacao

A implementacao so esta concluida se todos os itens abaixo forem demonstrados:

1. `--profile feminino` sem `--discovery-scope` permanece com comportamento e fontes atuais.
2. `--profile feminino --discovery-scope calcado` carrega somente as 11 keywords aprovadas.
3. `--profile feminino --discovery-scope moda` usa somente as keywords do grupo macro `moda`.
4. `--profile feminino --discovery-scope cabelo` usa somente as keywords do grupo macro `cabelo`.
5. A flag nao percorre keywords de outros grupos femininos atuais.
6. O profile carregado continua sendo `feminino`.
7. A saida do scope mantem `catalog_profile_slug=feminino`.
8. A saida focada fica isolada por escopo e nao sobrescreve rodadas completas.
9. Nenhum `[[profiles]] slug = "feminino-calcados"` e criado.
10. O suporte a `--discovery-scope` e generico para qualquer grupo macro existente em `profile.subniches[].slug`, sem hardcode de `calcado`, `moda` ou `cabelo`.
11. Um novo grupo macro adicionado a `profile.subniches` fica automaticamente habilitado como flag quando possuir `keyword_terms`.
12. Um escopo inexistente falha antes de chamar o provider.
13. Um grupo macro sem `keyword_terms` falha antes de chamar o provider com erro claro.
14. Todo `target_subniche` declarado no grupo macro e validado contra `allowed_subniches` da taxonomia vigente do profile.
15. Um grupo macro com `target_subniche` inexistente falha antes de chamar o provider.
16. Nenhum grupo, destino de publicacao ou configuracao n8n/WhatsApp e criado.
17. Nenhuma regra de score, fallback, cooldown, dedup ou selecao e modificada.
18. Os testes existentes continuam passando.

## Testes minimos de regressao

Antes da implementacao, capturar a configuracao carregada do profile `feminino`.

Depois da implementacao, provar:

```text
feminino_before_sem_scope == feminino_after_sem_scope
```

Validar tambem:

```text
set(feminino.subniches["calcado"].keyword_terms) == {
  sandalia,
  sapatilha,
  chinelo,
  rasteirinha,
  rasteira,
  mocassim,
  loafer,
  papete,
  tamanco,
  slide,
  birken
}
```

E provar que uma execucao planejada para o builder com scope usa:

```text
profile.slug == feminino
discovery_scope == calcado
target_subniches == somente subnichos existentes em allowed_subniches
collection_keywords == somente as 11 aprovadas
```

Tambem provar que execucoes por grupos macro existentes funcionam sem cadastro adicional:

```text
profile.slug == feminino
discovery_scope == moda
collection_keywords == feminino.subniches["moda"].keyword_terms
```

```text
profile.slug == feminino
discovery_scope == cabelo
collection_keywords == feminino.subniches["cabelo"].keyword_terms
```

Tambem validar que:

```text
feminino-calcados != profile operacional
feminino-calcados != destino operacional
feminino-calcados != novo grupo
feminino-calcados != nova regra editorial
```

## Regra de contencao

Antes de qualquer alteracao, aplicar a pergunta:

> Esta mudanca e estritamente necessaria para executar `--profile feminino --discovery-scope calcado` usando o builder atual e mantendo a identidade operacional como `feminino`?

Se a resposta for nao, a mudanca esta fora do escopo.

Nao fazer:

- refatoracao oportunista;
- correcao de problemas paralelos;
- reorganizacao de configuracao existente;
- renomeacao de estruturas atuais;
- profile tecnico `feminino-calcados`;
- normalizacao posterior `feminino-calcados -> feminino`;
- alteracao de Supabase;
- alteracao de publicacao;
- mudanca de comportamento dos profiles atuais.

## Resultado esperado

Depois da implementacao existirao dois modos do mesmo profile operacional:

```text
shopee-catalog-builder --profile feminino
-> comportamento atual intacto
-> usa keyword_terms completas do feminino
-> saida de profile feminino
```

```text
shopee-catalog-builder --profile feminino --discovery-scope calcado
-> discovery apenas pelas 11 keywords aprovadas
-> aplica as travas negativas do profile feminino
-> deduplicacao e persistencia pelo mecanismo existente
-> saida isolada por escopo
-> saida de profile feminino
-> pronta para importacao controlada posterior como profile=feminino
```

## Prompt para o Codex implementar esta spec

```text
Implemente a spec `docs/projeto/10-spec-discovery-calcados-feminino.md` no repositorio atual.

PRINCIPIO MAIS IMPORTANTE: a mudanca deve ser cirurgica, aditiva e com regressao zero. Nao crie o profile tecnico `feminino-calcados`; a identidade operacional deve continuar sendo `feminino`.

Antes de editar:
1. Leia `AGENTS.md` e siga todas as instrucoes do repositorio.
2. Leia integralmente `docs/projeto/10-spec-discovery-calcados-feminino.md`.
3. Inspecione `config/shopee_catalog_profiles.toml`.
4. Inspecione o loader de profiles e o `shopee_catalog_builder` apenas para confirmar o contrato atual.
5. Capture a configuracao atual do profile `feminino` para provar que ficara inalterada quando a flag nao for usada.

IMPLEMENTACAO ESPERADA:
- adicionar suporte generico a `--discovery-scope <scope>` no builder Shopee;
- aceitar automaticamente como scope qualquer grupo macro presente em `profile.subniches[].slug`;
- usar as keywords do grupo macro em `profile.subniches[].keyword_terms`;
- adicionar a configuracao declarativa do grupo macro `calcado` dentro do profile `feminino`;
- declarar `target_subniches` do grupo `calcado` apontando somente para os cinco subnichos de calcados ja existentes na taxonomia feminina;
- validar `target_subniches` contra `allowed_subniches` de `config/catalog-taxonomies/feminino/shopee_feminino_subniches_taxonomia_base.json`;
- usar exatamente estas keywords simples: `sandalia`, `sapatilha`, `chinelo`, `rasteirinha`, `rasteira`, `mocassim`, `loafer`, `papete`, `tamanco`, `slide`, `birken`;
- nao adicionar `feminino` as keywords;
- quando a flag for usada, coletar somente as keywords do scope;
- quando a flag nao for usada, preservar exatamente as keywords atuais do profile;
- manter `catalog_profile_slug=feminino` nos artefatos;
- isolar a saida do scope para nao sobrescrever rodadas completas;
- NAO criar `[[profiles]] slug = "feminino-calcados"`;
- NAO criar normalizacao posterior de profile;
- NAO alterar provider Shopee, paginacao, dedup, filtros globais, classificacao, score, cooldown, fallback, selecao, horarios, Supabase, n8n, WhatsApp ou WAHA.

VALIDACAO OBRIGATORIA:
1. Rode os testes relevantes do loader/configuracao e os testes existentes relacionados ao catalogo Shopee.
2. Prove que `--profile feminino` sem scope carrega a mesma configuracao e percorre as mesmas keywords de antes.
3. Prove que `--profile feminino --discovery-scope calcado` usa somente as 11 keywords aprovadas.
4. Prove que `--profile feminino --discovery-scope moda` usa somente as keywords do grupo macro `moda`.
5. Prove que `--profile feminino --discovery-scope cabelo` usa somente as keywords do grupo macro `cabelo`.
6. Prove que a saida focada preserva `catalog_profile_slug=feminino` e registra `discovery_scope=calcado`.
7. Prove que nao existe profile operacional `feminino-calcados`.
8. Prove que um novo grupo macro adicionado a `profile.subniches` fica automaticamente habilitado como flag quando possuir `keyword_terms`.
9. Prove que um escopo inexistente falha antes de chamar o provider.
10. Prove que grupo macro sem `keyword_terms` falha antes de chamar o provider com erro claro.
11. Prove que `target_subniches` do grupo `calcado` e validado contra `allowed_subniches` da taxonomia vigente do profile.
12. Prove que um `target_subniche` inexistente falha antes de chamar o provider.
13. Rode a suite existente suficiente para demonstrar ausencia de regressao.
14. Mostre o diff final e explique arquivo por arquivo por que cada alteracao foi indispensavel.

CONTENCAO DE ESCOPO:
Se durante a implementacao voce concluir que precisa alterar schema, Supabase, selecao, taxonomia, n8n, publicacao ou qualquer componente fora da flag/configuracao de discovery, NAO faca a alteracao automaticamente. Pare essa parte, documente a incompatibilidade encontrada e explique por que a spec precisa ser reavaliada.

Nao aproveite esta tarefa para corrigir ou refatorar qualquer outro ponto do projeto.
```

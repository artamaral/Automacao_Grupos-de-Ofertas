# 10 — Spec de Discovery Cirúrgico de Calçados Feminino

## Status

Proposta pronta para implementação.

## Objetivo

Adicionar uma capacidade **isolada, cirúrgica e exclusivamente aditiva** para descobrir produtos de calçados femininos na Shopee, sem alterar qualquer comportamento, regra, configuração ou fluxo já existente.

A mudança deve permitir executar discovery somente para calçados, reaproveitando o mecanismo atual de coleta por `keyword_terms`.

## Princípio obrigatório: regressão zero

Tudo que já existe deve permanecer intacto.

Esta implementação **não pode alterar**:

- o profile `feminino` existente;
- as `keyword_terms` atuais do profile `feminino`;
- os subnichos atuais do profile `feminino`;
- discovery dos demais nichos;
- `shopee_catalog_builder`;
- algoritmo de coleta;
- paginação;
- deduplicação;
- filtros negativos existentes;
- classificação atual de itens já existentes;
- score comercial;
- cooldown;
- fallback;
- seleção editorial;
- regras de rotação;
- horários;
- quantidade de mensagens já existentes;
- publicação;
- Supabase;
- n8n;
- WhatsApp;
- WAHA;
- contratos downstream.

A implementação deve ser declarativa sempre que possível. Não fazer refatorações oportunistas, limpeza de código, reorganização de profiles ou qualquer mudança não necessária para criar o novo caminho de discovery.

## Contexto técnico confirmado

O builder atual recebe um `--profile`, carrega suas `keyword_terms` e executa uma coleta `productOfferV2(keyword=...)` para cada termo configurado.

O CLI atual já possui o comportamento necessário para executar um profile composto apenas por keywords de calçados. Portanto, esta spec **não prevê alteração no CLI nem no código compartilhado do builder**.

O profile `feminino` atual não contém keywords específicas de calçados. O arquivo de taxonomia feminina também não contém atualmente os novos subnichos de calçados.

## Nova capacidade permitida

Criar um novo profile técnico de discovery:

```text
feminino-calcados
```

Esse profile existe exclusivamente para coleta de candidatos de calçados.

Ele:

- não representa novo nicho comercial;
- não cria novo grupo de WhatsApp;
- não cria novo fluxo de publicação;
- não altera o profile `feminino`;
- não substitui o profile `feminino`;
- não deve ser usado como destino operacional final;
- deve gerar saída isolada por profile;
- deve poder ser executado sem disparar as keywords atuais do profile `feminino`.

## Keywords de discovery

Usar somente termos simples, sem obrigar a palavra `feminino` na query.

Conjunto aprovado:

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

A adição de `feminino` às queries, como `chinelo feminino`, reduz o recall e pode deixar de recuperar produtos válidos cujo título contenha apenas `chinelo`, `slide`, `papete` etc.

O discovery deve privilegiar recall e deixar a contenção de resultados inadequados para as mesmas travas negativas já usadas no universo feminino.

## Validação com amostra real

Foi analisado o arquivo:

```text
BatchProductLinks20260825161442-ad1b1e5c698c47b49c14c5de292bd968.csv
```

A amostra contém **67 itens**.

Aplicando correspondência textual normalizada sobre `Item Name`, o conjunto aprovado de 11 termos simples cobriu:

```text
67 / 67 itens = 100% da amostra
```

Cobertura observada por termo na amostra:

| Keyword | Itens com correspondência |
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

Há sobreposição entre keywords; isso é esperado e deve continuar sendo tratado pela deduplicação já existente.

A cobertura de 100% vale para esta amostra e **não deve ser interpretada como garantia universal de cobertura de todo o catálogo da Shopee**.

## Feminino sem forçar `feminino` na keyword

Não adicionar `feminino` às queries de discovery apenas para reforçar o gênero.

O novo profile técnico deve aplicar as mesmas travas negativas relevantes já existentes no profile feminino para rejeitar resultados claramente inadequados, incluindo termos como:

```text
masculino
masculin
for men
for man
```

além das demais exclusões já existentes e aplicáveis.

### Regra de segurança da implementação

Não modificar os `negative_terms` do profile `feminino`.

Para o novo profile `feminino-calcados`, deve-se **reproduzir declarativamente** o conjunto vigente de travas relevantes do feminino, ou reutilizá-lo apenas se isso já for suportado pela configuração atual sem mudança de código compartilhado.

Se reutilização exigir refatoração do loader, herança nova ou alteração de código compartilhado, não fazer. Nesse caso, duplicar declarativamente os termos no novo profile é preferível porque preserva o caráter cirúrgico da mudança.

## Relação entre keywords e subnichos

Keyword de discovery não é equivalente a subnicho editorial.

Termos como:

```text
papete
tamanco
slide
birken
```

podem ser usados para descobrir produtos sem criar subnichos com esses nomes.

Os subnichos finais aprovados para a expansão de calçados continuam sendo:

```text
calcados-sandalia
calcados-sapatilha
calcados-chinelo
calcados-rasteirinha
calcados-mocassim
```

Esta spec, porém, cobre **somente o discovery isolado**. A classificação definitiva e a expansão da taxonomia devem seguir a spec/etapa específica de taxonomia e planejamento, sem serem antecipadas por esta implementação.

## Arquivo preferencial de alteração

A modificação deve ficar, preferencialmente, restrita a:

```text
config/shopee_catalog_profiles.toml
```

Adicionar um novo bloco `[[profiles]]` com `slug = "feminino-calcados"`.

Não modificar o bloco existente:

```text
slug = "feminino"
```

## Estrutura esperada do novo profile

A forma exata deve respeitar o contrato atual de `config/shopee_catalog_profiles.toml`.

Exemplo conceitual:

```toml
[[profiles]]
slug = "feminino-calcados"
name = "Feminino - Calçados"
keyword_terms = [
  "sandalia",
  "sapatilha",
  "chinelo",
  "rasteirinha",
  "rasteira",
  "mocassim",
  "loafer",
  "papete",
  "tamanco",
  "slide",
  "birken",
]

negative_terms = [
  # copiar apenas conforme contrato vigente do feminino;
  # não alterar o profile feminino.
]

shop_ids = []
shop_names = []
```

Se o schema exigir outros campos obrigatórios, preenchê-los seguindo exatamente o padrão já existente, sem introduzir novas abstrações.

## Execução esperada

O novo discovery deve poder ser executado pelo CLI existente:

```bash
shopee-catalog-builder --profile feminino-calcados
```

Não adicionar flags como:

```text
--only-keywords
--subniche
--calcados
```

Não criar novo CLI, novo collector, novo provider ou novo método de acesso à Shopee.

## Isolamento de saída

A rodada deve usar o isolamento já existente por slug do profile, resultando em algo equivalente a:

```text
.data/shopee_catalog/feminino-calcados/<run-id>/
```

A execução não deve sobrescrever nem modificar:

```text
.data/shopee_catalog/feminino/
```

nem artefatos de outros profiles.

## Fora de escopo

Esta entrega não deve:

- mesclar automaticamente o resultado no catálogo operacional feminino;
- promover itens para produção;
- alterar Supabase;
- alterar `catalog_items`;
- adicionar slots de publicação;
- implementar `+2` mensagens por hora;
- alterar as atuais 112 mensagens/dia;
- alterar distribuição editorial;
- alterar score;
- alterar cooldown;
- alterar fallback;
- criar regra de rotação;
- criar regra específica de escolha por horário;
- mudar seleção dos itens existentes;
- alterar taxonomia existente;
- criar novos contratos downstream.

Esses assuntos pertencem às etapas específicas de taxonomia/planejamento e não fazem parte desta mudança de discovery.

## Critérios de aceitação

A implementação só está concluída se todos os itens abaixo forem demonstrados:

1. O profile `feminino` permanece inalterado em comportamento e conteúdo dentro de `config/shopee_catalog_profiles.toml`.
2. O novo profile `feminino-calcados` é carregado pelo loader existente sem mudança de código compartilhado.
3. O novo profile contém somente as 11 keywords aprovadas de calçados.
4. A execução de `--profile feminino-calcados` não percorre keywords de maquiagem, skincare, cabelo, moda geral ou outros grupos femininos já existentes.
5. A execução de `--profile feminino` continua funcionando exatamente como antes.
6. Nenhuma mudança é necessária em `shopee_catalog_builder`.
7. Nenhuma mudança é necessária nos providers Shopee.
8. A saída de `feminino-calcados` fica isolada por slug.
9. Nenhum grupo, destino de publicação ou configuração n8n/WhatsApp é criado.
10. Nenhuma regra de score, fallback, cooldown, dedup ou seleção é modificada.
11. Os testes existentes continuam passando.
12. Testes adicionais devem ser criados apenas se necessários para provar o carregamento do novo profile e a ausência de regressão no profile `feminino`.

## Testes mínimos de regressão

Antes da implementação, capturar a configuração carregada do profile `feminino`.

Depois da implementação, provar:

```text
feminino_before == feminino_after
```

Validar também:

```text
set(feminino_calcados.keyword_terms) == {
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

E provar que:

```text
feminino-calcados != destino operacional
feminino-calcados != novo grupo
feminino-calcados != nova regra editorial
```

## Regra de contenção

Antes de qualquer alteração, aplicar a pergunta:

> Esta mudança é estritamente necessária para criar ou executar o profile técnico `feminino-calcados` usando o builder atual?

Se a resposta for não, a mudança está fora do escopo.

Não fazer:

- refatoração oportunista;
- correção de problemas paralelos;
- reorganização de configuração existente;
- renomeação de estruturas atuais;
- abstração nova para compartilhamento de `negative_terms`;
- alteração de código compartilhado para reduzir duplicação;
- mudança de comportamento dos profiles atuais.

## Resultado esperado

Depois da implementação existirão dois caminhos independentes:

```text
feminino
→ comportamento atual intacto
```

```text
feminino-calcados
→ discovery apenas pelas 11 keywords aprovadas
→ aplicação das travas negativas próprias do novo profile
→ deduplicação e persistência pelo mecanismo já existente
→ saída isolada
```

A única nova capacidade operacional deve ser a possibilidade de executar o builder atual com:

```bash
shopee-catalog-builder --profile feminino-calcados
```

## Prompt para o Codex implementar esta spec

```text
Implemente a spec `docs/projeto/10-spec-discovery-calcados-feminino.md` no repositório atual.

PRINCÍPIO MAIS IMPORTANTE: a mudança deve ser cirúrgica, estritamente aditiva e com regressão zero. Não altere nada que já exista além do mínimo indispensável para adicionar o novo profile técnico `feminino-calcados`.

Antes de editar:
1. Leia `AGENTS.md` e siga todas as instruções do repositório.
2. Leia integralmente `docs/projeto/10-spec-discovery-calcados-feminino.md`.
3. Inspecione `config/shopee_catalog_profiles.toml`.
4. Inspecione o loader de profiles e o `shopee_catalog_builder` apenas para confirmar o contrato atual. Não refatore esses componentes.
5. Capture a configuração atual do profile `feminino` para provar que ficará inalterada.

IMPLEMENTAÇÃO ESPERADA:
- adicionar um novo `[[profiles]]` em `config/shopee_catalog_profiles.toml` com slug `feminino-calcados`;
- usar exatamente estas keywords simples: `sandalia`, `sapatilha`, `chinelo`, `rasteirinha`, `rasteira`, `mocassim`, `loafer`, `papete`, `tamanco`, `slide`, `birken`;
- não adicionar `feminino` às keywords;
- aplicar no novo profile as travas negativas relevantes já existentes no profile feminino, de forma declarativa;
- NÃO modificar o bloco atual do profile `feminino`;
- NÃO criar herança/refatoração para compartilhar configuração se isso exigir mudança de código comum;
- NÃO alterar `shopee_catalog_builder` se o profile já puder ser carregado pelo contrato atual;
- NÃO criar CLI novo nem novas flags;
- NÃO alterar provider Shopee, paginação, dedup, filtros globais, classificação, score, cooldown, fallback, seleção, horários, Supabase, n8n, WhatsApp ou WAHA;
- NÃO implementar ainda a expansão de taxonomia nem o +2 mensagens/hora; isso está fora desta spec.

VALIDAÇÃO OBRIGATÓRIA:
1. Rode os testes relevantes do loader/configuração e os testes existentes relacionados ao catálogo Shopee.
2. Prove que o profile `feminino` antes e depois possui exatamente a mesma configuração.
3. Prove que `feminino-calcados` contém somente as 11 keywords aprovadas.
4. Prove que o builder para `feminino-calcados` usa somente essas keywords e produz saída isolada por slug.
5. Rode a suíte existente suficiente para demonstrar ausência de regressão.
6. Mostre o diff final e explique arquivo por arquivo por que cada alteração foi indispensável.

CONTENÇÃO DE ESCOPO:
Se durante a implementação você concluir que precisa alterar código compartilhado, schema, Supabase, seleção, taxonomia, n8n, publicação ou qualquer componente fora da inclusão declarativa do novo profile, NÃO faça a alteração automaticamente. Pare essa parte, documente a incompatibilidade encontrada e explique por que a spec não pode ser cumprida de forma puramente aditiva.

Não aproveite esta tarefa para corrigir ou refatorar qualquer outro ponto do projeto.
```

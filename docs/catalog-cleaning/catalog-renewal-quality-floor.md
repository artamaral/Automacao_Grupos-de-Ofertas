# Regra de renovação do catálogo por qualidade comercial

## Objetivo

Reduzir a dominância do catálogo legado na seleção de publicação sem alterar a fórmula `commercial_v1` e sem excluir fisicamente os itens existentes.

A regra atua somente sobre a elegibilidade do legado: itens legados abaixo de um piso de qualidade são **inativados** e deixam de competir nas seleções futuras. Itens novos continuam sendo avaliados normalmente pelo `commercial_v1`.

## Princípio

O diagnóstico mostrou que, principalmente em `moda`, o legado domina o topo do ranking por comissão histórica muito alta, mesmo quando os novos itens apresentam vendas e qualidade de loja significativamente melhores.

Para evitar mudar o score principal, a renovação deve usar um score auxiliar formado apenas pelos componentes que representam validação comercial:

```text
quality_score = sales_score + shop_score
```

Onde `sales_score` e `shop_score` são exatamente os mesmos componentes já usados pelo `commercial_v1`.

Não criar uma nova interpretação de vendas ou de tipo de loja. A regra de renovação deve reutilizar os componentes existentes.

## População de referência

Para cada macro-subnicho, calcular o `quality_score` dos **itens novos elegíveis** provenientes da execução de descoberta mais recente.

Um item novo é considerado elegível somente se já cumprir os critérios normais de entrada no catálogo operacional, incluindo taxonomia válida e rating mínimo vigente.

O piso recomendado para renovação é a **média do `quality_score` dos novos itens elegíveis do próprio macro-subnicho**.

```text
quality_floor[subniche] = mean(quality_score dos novos elegíveis do subniche)
```

A referência deve ser calculada por macro-subnicho; não usar um valor global único.

## Regra de inativação do legado

Para cada item legado ativo:

```text
legacy_quality_score = sales_score + shop_score

se legacy_quality_score < quality_floor[subniche]:
    inativar item legado
senão:
    manter item legado ativo
```

A regra:

- não altera `commercial_v1`;
- não altera o score persistido do item;
- não exclui o item do banco;
- não afeta diretamente itens recém-descobertos;
- apenas define se um item legado continua elegível para competir nas seleções;
- deve ser aplicada por macro-subnicho.

Itens que pertencem a mais de um macro-subnicho devem ser avaliados conforme a política de elegibilidade definida para cada associação. A implementação não deve assumir silenciosamente que um único piso global vale para todas as associações.

## Por que não usar somente vendas

Usar somente `sales` ou um corte fixo de vendas não captura a diferença de qualidade entre lojas e se comporta de forma diferente entre subnichos.

A composição `sales_score + shop_score` favorece itens que combinam tração real com qualidade de seller, exatamente os dois fatores nos quais os novos itens se mostraram superiores ao legado na análise.

Em `moda`, por exemplo, no top 50 analisado:

| Componente | Top 50 legado | Top 50 novos |
|---|---:|---:|
| `sales_score` | 4,15 | 9,41 |
| `shop_score` | 1,80 | 5,50 |
| `sales_score + shop_score` | 5,95 | 14,91 |

Apesar disso, o legado mantinha vantagem no `commercial_v1` devido principalmente à comissão:

| Componente | Top 50 legado | Top 50 novos |
|---|---:|---:|
| comissão | 49,12 | 17,98 |
| desconto | 14,46 | 18,65 |
| vendas | 4,15 | 9,41 |
| rating | 10,00 | 10,00 |
| loja | 1,80 | 5,50 |
| score médio | 79,53 | 61,54 |

Assim, a regra de renovação não substitui o `commercial_v1`; ela remove da competição o legado cuja permanência é sustentada principalmente por comissão histórica, mas que não apresenta validação comercial compatível com o catálogo recém-descoberto.

## Resultado da simulação

Usando como piso a **média de `sales_score + shop_score` dos novos elegíveis** e aplicando o corte somente para inativar legado, a simulação de top 50 produziu:

| Macro-subnicho | Piso médio | Legados ativos após corte | Novos no top 50 | % novo no top 50 |
|---|---:|---:|---:|---:|
| moda | 8,08 | 1.140 | 15 | 30% |
| maquiagem | 6,46 | 726 | 15 | 30% |
| skincare | 10,60 | 80 | 28 | 56% |
| cabelo | 9,65 | 728 | 5 | 10% |
| acessórios | 5,28 | 154 | 17 | 34% |
| unhas | 6,49 | 153 | 19 | 38% |

Para referência, antes da regra a participação de novos no top 50 era aproximadamente:

| Macro-subnicho | % novo sem regra |
|---|---:|
| moda | 4% |
| maquiagem | 20% |
| skincare | 6% |
| cabelo | 0% |
| acessórios | 4% |
| unhas | 24% |

A regra, portanto, aumenta a renovação sem modificar o score principal e sem remover fisicamente o histórico do catálogo.

## Média versus mediana

Também foi simulada a mediana do `quality_score` dos novos como piso. O resultado foi menos consistente entre os subnichos.

| Macro-subnicho | Piso média | % novo top 50 | Piso mediana | % novo top 50 |
|---|---:|---:|---:|---:|
| moda | 8,08 | 30% | 10,00 | 30% |
| maquiagem | 6,46 | 30% | 5,00 | 22% |
| skincare | 10,60 | 56% | 10,00 | 42% |
| cabelo | 9,65 | 10% | 10,00 | 10% |
| acessórios | 5,28 | 34% | 5,00 | 10% |
| unhas | 6,49 | 38% | 5,00 | 24% |

Por isso, a decisão atual é usar **a média por macro-subnicho** como referência da regra de renovação.

## Ciclo de execução

A regra deve ser executada após uma nova rodada de descoberta estar pronta e antes de a nova composição do catálogo ser usada para seleção operacional.

Fluxo conceitual:

1. executar descoberta;
2. limpar/classificar os itens novos;
3. identificar itens realmente novos por `itemId`;
4. selecionar os novos elegíveis;
5. calcular `quality_score = sales_score + shop_score`;
6. calcular a média por macro-subnicho;
7. comparar itens legados ativos com o piso correspondente;
8. inativar somente os legados abaixo do piso;
9. manter o `commercial_v1` inalterado para ranking/publicação;
10. registrar os totais de ativos/inativos e o piso utilizado por subnicho.

## Reativação

A inativação deve ser reversível. Caso um item legado seja reavaliado em uma descoberta futura e seus dados de vendas/loja passem a superar o piso vigente, ele pode voltar a ser ativo conforme a política de atualização do catálogo.

Não implementar deleção permanente como parte desta regra.

## Observabilidade mínima

Cada execução deve permitir auditar pelo menos:

- data/run da descoberta usada como referência;
- macro-subnicho;
- quantidade de novos elegíveis;
- média de `quality_score` usada como piso;
- quantidade de legados avaliados;
- quantidade de legados mantidos ativos;
- quantidade de legados inativados;
- quantidade de itens novos que entram no top 50 pós-regra;
- percentual de novos no top 50 pós-regra.

## Fora de escopo desta regra

Esta regra não deve:

- alterar pesos do `commercial_v1`;
- alterar taxonomia;
- alterar critérios de rating;
- alterar cooldown de publicação;
- criar um novo score de ranking de publicação;
- apagar itens do catálogo;
- substituir os critérios normais de descoberta/importação.

Ela existe somente para **renovar a população elegível do legado** antes do ranking normal de publicação.
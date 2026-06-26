# Scoring operacional

Este documento define a regra atual do `ScorerAgent`. O objetivo e manter o
ranking simples, auditavel e calibravel, sem transformar sinais ainda instaveis
da Shopee ou da Amazon em regra rigida antes de existir historico suficiente.

## Papel no fluxo

O scorer entra depois do `Collector` e antes do `Copywriter`:

```text
Catalogo curado ou provider -> Collector -> Scorer -> Copywriter -> Compliance
```

Entrada:

- lista de `Offer` normalizada;
- sinais comuns entre providers: preco, preco anterior, comissao, vendas,
  avaliacao, frete, marketplace e nicho.

Saida:

- lista de `ScoredOffer`;
- `score` numerico;
- `reasons` com os motivos exibiveis para revisao humana e copy.

## Principios

- O score atual mede qualidade comercial basica da oferta.
- O score ainda nao mede aderencia fina ao grupo.
- Aderencia, classificacao por subnicho e roteamento devem evoluir como camadas
  separadas.
- A regra deve continuar explicavel por componentes.
- Ponderacao fina deve ser calibrada com evidencia de catalogos e aprovacoes
  reais, nao por suposicao.

## Componentes atuais

| Componente | Regra | Pontos | Motivo |
| --- | --- | --- | --- |
| Desconto | entra a partir de 20% | `min(desconto, 60) * 1.2` | `desconto de X%` |
| Comissao | entra quando maior que zero | `commission_rate * 100` | `comissao de X%` |
| Vendas | entra a partir de 100 vendas | `min(vendas / 100, 20)` | `X vendas` |
| Avaliacao | entra a partir de 4.5 | `10` | `avaliacao X.X` |
| Frete | entra quando o provider normaliza frete/prime | `8` | `frete rapido/gratis` |
| Tipo de loja | entra quando houver `shopType` conhecido | `1 -> 10`, `4 -> 7`, `2 -> 5`, vazio -> `0` | `loja oficial`, `loja star+`, `loja star` |

Observacoes:

- desconto tem teto para evitar que um percentual muito alto domine sozinho;
- vendas tem teto para evitar que produtos muito vendidos bloqueiem achados
  novos com bons sinais;
- comissao ainda nao tem teto porque o projeto precisa observar mais dados
  reais antes de definir se isso prejudica a curadoria;
- frete depende de normalizacao confiavel do provider. Catalogos CSV da Shopee
  podem nao trazer esse sinal no modelo `Offer` atual.
- tipo de loja hoje usa a leitura operacional do `shopType` do catalogo:
  `1` Shopee Mall / loja oficial, `4` Star+ Shop, `2` Star Shop, vazio = loja comum.

## Decisao operacional atual para mae-e-bebe

Na analise operacional do nicho `mae-e-bebe`, a leitura atual e:

- cerca de `91%` das vendas observadas vem de lojas com `ratingStar >= 4.8`;
- dentro desse bloco principal de vendas, aproximadamente:
  `11%` vem de `shopType 1` (Shopee Mall / loja oficial),
  `54%` vem de `shopType 2` (Star Shop),
  `27%` vem de itens sem `shopType`.

Decisao registrada a partir dessa leitura:

- para as proximas rodadas de achados, o catalogo inicial deve priorizar itens
  com `ratingStar >= 4.8`;
- itens abaixo dessa faixa devem ficar fora do recorte operacional inicial;
- `shopType 2` deve receber majoracao no ranking, porque concentra a maior parte
  das vendas dentro do bloco de melhor nota em `mae-e-bebe`.

Leitura pratica desta decisao:

- `shopType 1` continua sendo forte sinal de confianca institucional;
- `shopType 2` passa a ser tratado tambem como forte sinal comercial, nao apenas
  como selo secundario;
- itens sem `shopType` continuam elegiveis, mas nao devem superar facilmente
  itens `shopType 2` quando os demais sinais forem parecidos.

Mesmo restringindo a leitura ao bloco com `ratingStar = 5`, ainda existe uma
diferenca importante de faixa de preco entre os tipos de loja:

- `shopType 1` opera em faixa claramente mais alta, com media de `209,53`,
  mediana de `104,9`, terco baixo em `31,69` e terco alto em `489,1`;
- `shopType 2` fica num patamar intermediario e mais operacional para achados,
  com media de `100,44`, mediana de `49,72`, terco baixo em `24,83` e terco
  alto em `225,34`;
- itens sem `shopType` ficam proximos de `shopType 2` no miolo da distribuicao,
  com media de `92,46`, mediana de `49,9`, terco baixo em `24,51` e terco alto
  em `200,39`.

Leitura operacional de preco:

- `shopType 1` sinaliza mais confianca institucional, mas tambem empurra o
  ranking para ticket mais alto;
- `shopType 2` concentra melhor equilibrio entre vendas, confianca e faixa de
  preco adequada para rodada recorrente de achados;
- itens sem `shopType` continuam relevantes, mas em geral competem com
  `shopType 2` sem mostrar a mesma forca comercial.

## O que ainda nao entra no score

Fica fora por enquanto:

- subnicho;
- grupo de destino;
- risco de item fora de contexto;
- cupom;
- validade de campanha;
- prazo real de entrega;
- reputacao detalhada da loja;
- historico de aprovacao/rejeicao humana;
- performance posterior do grupo.

Esses pontos devem entrar em camadas futuras de classificacao, roteamento e
calibragem, sem quebrar o contrato atual de `ScoredOffer`.

## Proximas evolucoes

1. Separar explicitamente `commercial_score` de `fit_score`.
2. Guardar componentes de score em estrutura persistivel quando houver banco ou
   artefato de ranking dedicado.
3. Criar score proprio para cupons.
4. Definir score minimo por grupo somente depois de observar aprovacoes e
   rejeicoes reais.
5. Usar historico de revisao humana para calibrar pesos.

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

Contrato posterior:

- a saida do scorer deve alimentar um `CopyBrief` antes da geracao de texto;
- o `CopyBrief` transforma `ScoredOffer` em entrada factual para copywriter GPT;
- GPT nao deve receber responsabilidade de decidir score ou inventar motivo;
- GPT deve apenas redigir a partir dos fatos, motivos e restricoes do brief.
- antes do `CopyBrief`, precisa existir uma camada de selecao operacional;
- o scorer pode rankear toda a base elegivel, mas o copywriter nao deve receber
  automaticamente todos os itens pontuados.

## Gate entre score e copy

Entre `Scorer` e `Copywriter` deve existir um gate explicito de selecao:

```text
Catalogo curado ou provider
  -> Collector
  -> Scorer
  -> SelectionGate
  -> CopyBrief
  -> Copywriter GPT
  -> Compliance
```

Responsabilidades do `SelectionGate`:

- decidir quais itens do ranking avancam para copy;
- registrar por que cada item foi selecionado, adiado ou bloqueado;
- aplicar regras temporais para evitar reciclagem infinita do mesmo item;
- aplicar bandas de distribuicao por nicho e subnicho;
- controlar deduplicacao de itens muito parecidos;
- garantir rechecagem final de preco e comissao antes do `CopyBrief`.

Contrato esperado de saida:

- `SelectedOffer` ou estrutura equivalente;
- `offer`;
- `score`;
- `reasons` do scorer;
- `selection_reason`;
- `selected_at`;
- `cooldown_until`;
- `selection_bucket` por nicho/subnicho;
- `refresh_status` da rechecagem final de preco/comissao.

### Regra de corte dentro do subnicho

A cota do subnicho deve ser aplicada apenas sobre itens elegiveis.

Ordem correta:

1. filtrar itens elegiveis do subnicho;
2. ordenar apenas os elegiveis por `score` desc;
3. selecionar os `N` primeiros da cota do subnicho;
4. ignorar itens nao elegiveis, mesmo que tenham score maior.

Exemplo registrado:

```text
subnicho: mamadeiras
cota: 2 itens

item | score | elegivel
1    | 20    | nao
2    | 19    | sim
3    | 18    | nao
4    | 17    | sim
```

Saida correta:

- item `2`
- item `4`

Leitura operacional:

- elegibilidade vem antes do corte por score;
- score ranqueia apenas dentro do conjunto que ja passou nas travas do gate.

### Regra de itens sem venda

Itens sem venda continuam elegiveis. Eles nao devem ser removidos por regra
cega, porque podem representar oportunidade negligenciada por outros
competidores.

Ao mesmo tempo, eles nao podem dominar a rodada.

Decisao registrada para a saida padrao de `mae-e-bebe`:

- itens com `sales = 0` podem entrar normalmente se estiverem bem rankeados;
- a selecao nao deve forcar preenchimento com itens sem venda;
- se a selecao natural produzir ate `4` itens sem venda, a regra segue sem
  interferencia;
- se a selecao natural ultrapassar `4` itens sem venda, os excedentes devem ser
  pulados;
- ao pular um excedente sem venda, o gate deve tentar preencher a cota com o
  proximo item elegivel do mesmo subnicho;
- se nao existir substituto elegivel naquele subnicho, o slot pode ficar vazio.

Config esperado:

- `selection.max_zero_sales_items_per_round`

## Regras operacionais da selecao

### 1. Recorrencia temporal

Ja fica registrada a decisao de que a data de selecao deve ser persistida.

Objetivo:

- impedir que a mesma oferta seja passada indefinidamente para frente;
- permitir que uma oferta volte a competir depois de um intervalo controlado.

Regra temporaria inicial:

- toda oferta selecionada deve gravar `selected_at`;
- a oferta entra em `cooldown` por uma janela simples configuravel;
- depois de estourar essa janela, a oferta volta a ser elegivel para selecao;
- a janela inicial deve ser unica e simples, sem diferenciar nicho, ate existir
  historico suficiente.

Config esperado:

- `selection.cooldown_hours_default`

Melhoria sugerida:

- depois, evoluir para `cooldown` por nicho, grupo ou tipo de oferta;
- manter tambem `last_sent_at` separado de `selected_at`, para nao misturar
  selecao interna com envio real.

### 2. Banda por nicho e subnicho

Nao deve existir distribuicao uniforme cega entre nichos e subnichos.

Motivo:

- alguns subnichos performam pior que outros;
- enviar o mesmo volume para todos distorce a rodada e ocupa espaco com itens
  de menor probabilidade operacional.

Decisao registrada:

- a selecao deve usar bandas por nicho e subnicho;
- essas bandas devem viver em config;
- a banda deve ser definida como percentual do total da rodada;
- a calibragem inicial deve vir de um histograma de vendas por nicho/subnicho,
  nao de intuicao.

Config esperado:

- `selection.band_allocation.<niche>.default_share_pct`
- `selection.band_allocation.<niche>.subniches.<subniche>.share_pct`

Regras praticas:

- a soma dos percentuais ativos de uma rodada deve fechar em `100`;
- quando um subnicho nao preencher sua propria banda, o saldo pode voltar para
  um pool redistribuivel do mesmo nicho;
- a banda limita o volume maximo, mas nao obriga preencher cota com item fraco.

Melhoria sugerida:

- manter junto no config a origem analitica da banda:
  `histogram_source`, `measured_at` e `sample_size`;
- recalibrar bandas por janela observada, nao por um snapshot isolado.

### 3. Similaridade e diversidade

Existe risco de a lista final ficar tomada por itens iguais ou quase iguais.

Problema operacional:

- muitos itens diferem pouco em titulo, kit, cor ou anuncio;
- isso reduz diversidade e impede giro de oportunidades.

Decisao registrada:

- a selecao deve aplicar uma regra de similaridade antes do copy;
- a regra deve considerar pelo menos descricao e vendedor;
- quando um item for bloqueado por similaridade, isso deve ser registrado como
  motivo especifico, e nao como queda silenciosa do score.

Config esperado:

- `selection.similarity.enabled`
- `selection.similarity.title_normalization`
- `selection.similarity.same_seller_bias`
- `selection.similarity.max_similar_items_per_cluster`
- `selection.similarity.cluster_cooldown_hours`

Regra operacional inicial sugerida:

- agrupar por titulo normalizado + vendedor normalizado;
- manter o melhor item do grupo por score;
- bloquear os demais como `similarity_suppressed`;
- itens bloqueados por similaridade nao devem ser tratados como rejeicao
  definitiva, porque podem voltar a ser uteis numa rodada futura.

Melhoria sugerida:

- separar `rejected_by_human` de `suppressed_by_similarity`;
- isso evita contaminar a proxima calibragem do score com bloqueios que foram
  apenas de diversidade da rodada.

### 4. Rechecagem final de preco e comissao

Como a lista de entrada pode envelhecer, o score nao deve ser considerado final
sem uma rechecagem operacional de preco e comissao.

Decisao registrada:

- todo item selecionado deve ter preco e comissao rechecados via API no final;
- se pelo menos um item mudar, a lista de score precisa ser recalculada;
- esse ciclo deve continuar ate que a lista de saida do score nao tenha mais
  itens desatualizados.

Leitura pratica:

- o copywriter GPT so deve receber itens ja rechecados;
- `CopyBrief` nao deve nascer de item com preco/comissao stale;
- a rodada precisa registrar quantas iteracoes de refresh foram necessarias.

Config esperado:

- `selection.refresh_before_copy.enabled`
- `selection.refresh_before_copy.max_iterations`
- `selection.refresh_before_copy.fields = ["price", "commission_rate"]`
- `selection.refresh_before_copy.stop_when_stable = true`

Registro obrigatorio:

- `refresh_iteration`;
- `fields_changed`;
- `stale_items_count`;
- `rescored_at`;
- `stability_reached`.

Melhoria sugerida:

- registrar tambem `price_delta_pct` e `commission_delta_pct` por item;
- se a lista nao estabilizar dentro do limite, bloquear a rodada para copy em
  vez de seguir com dado sabidamente velho.

## Proposta inicial de cota por subnicho para mae-e-bebe

Estudo usado nesta decisao:

- histograma de vendas por subnicho no catalogo `4.8+`;
- `score_medio_simples` por subnicho;
- `score_ponderado_por_vendas` por subnicho;
- piso inicial de volume em `vendas_totais >= 1000`.

Artefatos de apoio desta rodada:

- `tmp/mae-e-bebe-score-test-taxonomy/score_ponderado_por_subnicho.csv`
- `tmp/mae-e-bebe-score-test-taxonomy/tabela_proposta_decisao_subnichos.csv`
- `tmp/mae-e-bebe-score-test-taxonomy/subnichos_por_faixa_score_medio.csv`
- `tmp/mae-e-bebe-score-test-taxonomy/histograma_score_x_vendas.csv`

Decisao operacional inicial:

- rodada base de `20` itens para copywriter;
- itens sem venda podem entrar, mas nunca ultrapassar `4` itens na rodada;
- apenas subnichos que passam no piso de volume entram na banda principal;
- aplicar teto inicial de `2` itens por subnicho para evitar concentracao;
- dentro de cada subnicho, escolher os itens elegiveis de maior score.
- se nenhum parametro extra de selecao for informado, esta deve ser a saida
  padrao do harness para `mae e bebe`.

Distribuicao inicial proposta:

| Subnicho | Itens para copy | Motivo operacional |
| --- | ---: | --- |
| `amamentacao-extracao-leite` | `2` | maior massa de vendas do recorte |
| `roupas-body` | `2` | volume muito forte com score alto |
| `quarto-monitoramento` | `2` | massa relevante com boa base ativa |
| `higiene-saude-unhas` | `2` | volume forte e score ponderado alto |
| `higiene-saude-aspiradores-nasais` | `1` | bom equilibrio de massa e score |
| `passeio-canguru-ergonomico` | `1` | volume consistente no grupo principal |
| `roupas-geral` | `1` | score alto com vendas relevantes |
| `enxoval-kits` | `1` | bom equilibrio entre volume e score |
| `alimentacao-mamadeiras` | `1` | massa forte no recorte elegivel |
| `oral-mordedores-chupetas` | `1` | volume forte com boa leitura comercial |
| `alimentacao-copos-treinamento` | `1` | subnicho grande com score suficiente |
| `maternidade-bolsas-mochilas` | `1` | volume alto, merece presenca fixa |
| `troca-trocadores-portateis` | `1` | boa tracao no recorte principal |
| `brinquedos-montessori` | `1` | ajuda diversidade sem cair para cauda fraca |
| `passeio-carrinhos` | `1` | volume relevante no nicho |
| `banho-banheiras` | `1` | massa boa com score estavel |

Total da rodada base:

- `20` itens

Cadencia operacional registrada:

- `20` itens por execucao;
- minimo de `5` execucoes por dia;
- alvo operacional de `100` mensagens por dia.

Subnichos que ficam fora da banda principal nesta fase:

- subnichos abaixo do piso de volume;
- subnichos com score alto mas massa observada ainda pequena;
- subnichos que podem entrar depois como exploracao, nao como cota fixa.

Primeiros candidatos de reposicao ou exploracao:

- `alimentacao-cadeiras`
- `amamentacao-almofadas`
- `quarto-sono-mosquiteiros`
- `alimentacao-pratos-talheres`

Leitura pratica desta decisao:

- a banda principal tenta equilibrar massa de vendas com diversidade;
- nao segue distribuicao puramente proporcional, para evitar esmagar a rodada em
  poucos subnichos gigantes;
- tambem nao usa divisao uniforme, para evitar desperdiçar slots em cauda fraca.
- itens sem venda continuam entrando como exploracao, mas com teto global de
  `4` por rodada para nao contaminar a distribuicao principal.
- o harness nao deve sugerir ou aplicar criterio alternativo fora deste contrato
  quando nao houver parametro explicito do operador.

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
| Desconto | entra a partir de 20% | `min(desconto, 40) * 0.5` | `desconto de X%` |
| Comissao | entra quando maior que zero | `commission_rate * 100` | `comissao de X%` |
| Vendas | entra a partir de 100 vendas | `min(vendas / 100, 20)` | `X vendas` |
| Avaliacao | entra a partir de 4.5 | `10` | `avaliacao X.X` |
| Frete | entra quando o provider normaliza frete/prime | `8` | `frete rapido/gratis` |
| Tipo de loja | entra quando houver `shopType` conhecido | `1 -> 10`, `4 -> 7`, `2 -> 5`, vazio -> `0` | `loja oficial`, `loja star+`, `loja star` |

Observacoes:

- desconto tem teto para evitar que um percentual muito alto domine sozinho;
- desconto foi reduzido porque o percentual sozinho pode ser enganoso: uma loja
  pode subir o preco de referencia para exibir desconto maior sem necessariamente
  oferecer melhor oportunidade real;
- vendas tem teto para evitar que produtos muito vendidos bloqueiem achados
  novos com bons sinais;
- comissao ainda nao tem teto porque o projeto precisa observar mais dados
  reais antes de definir se isso prejudica a curadoria;
- no catalogo curado Shopee, `commission_rate` deve ser lida pela soma de
  `sellerCommissionRate + shopeeCommissionRate`; o campo `commissionRate`
  fica apenas como fallback quando essas duas parcelas nao vierem preenchidas;
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

## Validacao comparativa nos catalogos 4.8+

Com a regra atual aceita provisoriamente, foi rodado o mesmo teste de ranking
`top 10 por subnicho` sobre os catalogos operacionais validados `4.8+` dos tres
nichos atuais.

Recorte usado:

- `mae-e-bebe`: `39` subnichos, `360` itens no recorte final de top 10;
- `auto-e-moto`: `10` subnichos, `100` itens no recorte final de top 10;
- `feminino`: `31` subnichos, `310` itens no recorte final de top 10.

Breakdown por `shopType` dentro desse recorte:

- `mae-e-bebe`: `shopType 2 = 258 itens (71,67%)`,
  `sem shopType = 81 itens (22,5%)`,
  `shopType 1 = 21 itens (5,83%)`;
- `auto-e-moto`: `shopType 2 = 73 itens (73%)`,
  `sem shopType = 16 itens (16%)`,
  `shopType 1 = 11 itens (11%)`;
- `feminino`: `shopType 2 = 176 itens (56,77%)`,
  `sem shopType = 116 itens (37,42%)`,
  `shopType 1 = 18 itens (5,81%)`.

Leitura operacional desta validacao:

- `shopType 2` aparece como tipo dominante nos tops por subnicho dos tres
  nichos testados;
- `shopType 1` continua forte como sinal de confianca, mas nao domina volume no
  topo do ranking;
- itens sem `shopType` continuam aparecendo com frequencia relevante,
  principalmente em `feminino`, entao nao devem ser descartados;
- a majoracao de `shopType 2` continua coerente como regra inicial, porque ela
  conversa nao so com `mae-e-bebe`, mas tambem com os outros nichos testados.

Artefatos gerados nesta rodada:

- `tmp/mae-e-bebe-score-test-taxonomy/top10_por_subnicho.csv`
- `tmp/auto-e-moto-score-test-taxonomy/top10_por_subnicho.csv`
- `tmp/feminino-score-test-taxonomy/top10_por_subnicho.csv`

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

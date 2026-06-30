# Regras de Qualidade do Catálogo

Este documento define os critérios mínimos para uma oferta entrar no catálogo operacional do projeto.

## Objetivo

Evitar que produtos ruins, duplicados, incompletos ou pouco confiáveis cheguem à etapa de copy e revisão.

## Entrada esperada

Uma oferta pode vir de:

- catálogo curado local;
- mock/fixture;
- provider Shopee;
- provider Amazon;
- futura fonte controlada equivalente.

Independentemente da origem, ela deve ser convertida para o modelo interno antes de ser usada pelo pipeline.

## Campos mínimos

Uma oferta operacional deve ter, quando aplicável:

- marketplace;
- identificador ou link de origem;
- título;
- preço atual;
- imagem ou mídia válida;
- link de destino;
- nicho ou sinal de nicho;
- dados de reputação, vendas ou qualidade quando disponíveis;
- comissão ou sinal econômico quando disponível.

## Regras de remoção

Remover ou bloquear produtos que tenham:

- título vazio;
- preço ausente, zero ou inválido;
- link ausente;
- imagem obrigatória ausente quando a saída exigir mídia;
- desconto inconsistente;
- marketplace desconhecido;
- dados essenciais incompatíveis com o modelo interno;
- sinais claros de baixa qualidade ou risco para o usuário.

## Nota, vendas e reputação

Quando a origem disponibilizar nota, vendas ou reputação:

- preferir produtos com nota alta;
- preferir produtos com volume mínimo de vendas;
- penalizar produtos sem reputação quando houver alternativa equivalente melhor;
- não inventar nota, vendas ou prova social.

Valores exatos de corte devem ser definidos em spec ou configuração, não hardcoded sem justificativa.

## Deduplicação

Produtos duplicados devem ser detectados por combinação de sinais:

- marketplace;
- título normalizado;
- `item_id`, `product_id` ou equivalente quando existir;
- URL canônica;
- loja/vendedor;
- imagem;
- faixa de preço.

## Escolha do vencedor entre duplicados

Quando múltiplas ofertas representarem o mesmo produto, manter a melhor combinação de:

- preço mais atrativo;
- desconto válido;
- maior comissão quando isso não sacrificar qualidade;
- melhor reputação/vendas;
- melhor imagem;
- link mais confiável;
- aderência ao nicho.

## Nicho e subnicho

O nicho deve orientar curadoria e copy. Quando houver sinais como palavra-chave de origem, categoria ou `source_hits`, eles podem alimentar uma coluna ou campo de subnicho.

Exemplos:

```text
maquiagem -> base, corretivo, batom, pincel
cabelo -> shampoo, condicionador, escova secadora, óleo capilar
casa -> organizador, cozinha, limpeza, decoração
```

## Regras de preço

- `price` deve representar o preço atual.
- `old_price` só deve ser usado quando for maior que `price`.
- Percentual de desconto deve ser calculado, validado ou recebido de fonte confiável.
- Não afirmar que é o menor preço sem base verificável.

## Saída esperada

Após limpeza e ranqueamento, a lista deve conter apenas ofertas que possam ser transformadas em mensagem com baixo risco de erro.

## Relação com testes

Toda regra de remoção ou escolha automática deve ter teste quando virar comportamento de código.

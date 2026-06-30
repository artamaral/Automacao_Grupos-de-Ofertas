# Compliance de Afiliados

Este documento define regras de transparência e segurança para mensagens com links de afiliado.

## Objetivo

Garantir que toda mensagem gerada pelo projeto seja clara para o usuário final e não oculte a possibilidade de comissão.

## Regra obrigatória de disclosure

Toda mensagem que contenha link afiliado deve informar de forma simples que o link pode gerar comissão.

Exemplos aceitáveis:

```text
Aviso: este link pode gerar comissão para o canal, sem custo extra para você.
```

```text
Link de afiliado: podemos receber comissão pela compra, sem custo adicional.
```

## O que não fazer

- Não esconder que o link é de afiliado.
- Não afirmar parceria direta com marca ou marketplace sem confirmação.
- Não inventar cupom, desconto, frete grátis ou urgência.
- Não prometer preço permanente.
- Não afirmar que é o menor preço da internet sem fonte confiável.
- Não usar termos que possam confundir o usuário sobre a origem do link.

## Marketplace e origem

Quando a origem da oferta for conhecida, a mensagem pode mencionar o marketplace, desde que isso seja verdadeiro.

Exemplos:

```text
Oferta encontrada na Shopee.
```

```text
Oferta encontrada na Amazon.
```

## Preço e desconto

Preço e desconto devem vir de dado recebido ou cálculo verificável.

Formato recomendado de preço com desconto:

```text
Preço: de R$ 89.90 por R$ 49.90 (44% OFF)
```

Formato quando não houver preço antigo válido:

```text
Preço: R$ 49.90
```

## Cupons

Cupons só devem aparecer quando forem parte da entrada ou de fonte validada.

Não gerar automaticamente:

- cupom fictício;
- prazo fictício;
- limite de estoque sem confirmação;
- benefício exclusivo sem prova.

## Revisão humana

Antes de publicação real, a mensagem deve passar por revisão ou aprovação controlada. Na fase atual, o projeto deve permanecer em dry-run.

## Testes esperados

Comportamentos que devem ter teste quando implementados:

- bloquear mensagem com link afiliado e sem disclosure;
- bloquear preço inválido;
- bloquear desconto incoerente;
- preservar aviso de afiliado na copy final;
- não ativar publicação real com `ENABLE_REAL_PUBLISH=false`.

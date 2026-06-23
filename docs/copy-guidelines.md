# Guia de Copy das Ofertas

Este documento registra as regras de formatação das mensagens geradas pelo `CopywriterAgent`.

## Linha de preço

Quando a oferta possui preço antigo maior que o preço atual, usar o formato:

```text
Preço: de R$ 89.90 por R$ 49.90 (44% OFF)
```

Motivo:

- comunica o preço original antes do preço final;
- deixa mais clara a economia para o usuário;
- padroniza a copy para Shopee, Amazon e demais marketplaces.

Quando não existir preço antigo válido, usar:

```text
Preço: R$ 49.90
```

Se houver desconto calculado, o percentual deve aparecer ao final entre parênteses:

```text
Preço: R$ 49.90 (20% OFF)
```

## Transparência de afiliado

Toda mensagem deve conter aviso claro de afiliado, por exemplo:

```text
Aviso: este é um link de afiliado; podemos receber comissão pela compra. Preço e disponibilidade podem mudar.
```

Essa regra é validada pelo `ComplianceAgent` e coberta pelos testes automatizados.

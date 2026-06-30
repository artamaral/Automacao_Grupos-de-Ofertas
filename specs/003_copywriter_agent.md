# SPEC 003 — Copywriter Agent

Status: Rascunho

## Objetivo

Definir o comportamento do agente responsável por transformar uma oferta válida em mensagem curta, clara e compatível com as regras de afiliados.

## Contexto

O projeto já possui diretrizes de copy e compliance. Esta spec organiza o contrato esperado para mudanças futuras no agente de copy.

## Entrada

Oferta normalizada e, quando existir, pontuação ou contexto do nicho.

Campos relevantes:

```text
title
price
old_price
discount_percent
marketplace
affiliate_url
image_url
niche
subniche
coupon
expires_at
```

## Saída

Mensagem textual pronta para revisão humana ou para artefato dry-run.

## Regras obrigatórias

- Incluir aviso de afiliado quando houver link afiliado.
- Não prometer preço permanente.
- Não inventar urgência.
- Não inventar cupom.
- Não inventar frete grátis.
- Não afirmar menor preço sem fonte.
- Não esconder o marketplace quando ele for usado como argumento da copy.
- Usar formato de preço definido em `docs/copy-guidelines.md`.

## Linha de preço

Quando `old_price` for maior que `price`, usar:

```text
Preço: de R$ 89.90 por R$ 49.90 (44% OFF)
```

Quando não houver preço antigo válido:

```text
Preço: R$ 49.90
```

## Variação de texto

A variação deve ser controlada e testável. Ela pode mudar chamadas e frases, mas não deve alterar fatos da oferta.

## Fora de escopo

- Buscar produtos.
- Ranqueamento.
- Publicação real.
- Criação automática de imagem ou vídeo.

## Critérios de aceite

- Mensagem contém título ou descrição curta do produto.
- Mensagem contém preço formatado corretamente.
- Mensagem contém link quando a oferta tiver link.
- Mensagem com link afiliado contém disclosure.
- Mensagem não cria desconto, cupom ou urgência que não exista na entrada.

## Testes esperados

- Teste para linha de preço com `old_price` válido.
- Teste para linha de preço sem `old_price` válido.
- Teste para aviso de afiliado.
- Teste para não inserir urgência falsa.
- Teste para preservação do link.

## Harness / validação local

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --niche maquiagem --marketplace mock --dry-run
```

Validação operacional adicional:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
```

# SPEC 001 — Ingestão e Limpeza de Catálogo

Status: Rascunho

## Objetivo

Definir como o projeto deve receber uma lista controlada de produtos, validar campos mínimos, remover itens inválidos e entregar uma lista normalizada para o pipeline.

## Contexto

A decisão operacional atual é priorizar simplicidade: o fluxo principal deve trabalhar com catálogo curado ou fonte controlada, em vez de depender de exploração ampla diária de marketplaces.

## Entrada

Fonte controlada de ofertas, por exemplo:

- CSV;
- JSON;
- fixture local;
- provider mock;
- provider Shopee/Amazon com transport fake ou HTTP real explicitamente habilitado.

Campos desejados:

```text
marketplace
offer_id
title
price
old_price
url
affiliate_url
image_url
commission_rate
sales_count
rating
source_keyword
niche
subniche
```

## Saída

Lista normalizada de ofertas compatível com o modelo interno do projeto.

## Regras obrigatórias

- Remover oferta sem título.
- Remover oferta sem preço atual válido.
- Remover oferta sem link de destino.
- Remover oferta com marketplace desconhecido.
- Remover ou sinalizar oferta sem imagem quando a saída exigir mídia.
- Não inventar preço, nota, vendas, comissão ou desconto.
- Converter dados externos para modelo interno antes do scoring.
- Registrar motivo de remoção quando houver etapa de auditoria.

## Deduplicação

Duplicados devem ser detectados por sinais combinados:

- marketplace;
- `offer_id`, `item_id` ou equivalente;
- URL canônica;
- título normalizado;
- loja/vendedor;
- imagem;
- faixa de preço.

Quando houver duplicados, manter o melhor candidato considerando:

- preço;
- reputação/vendas;
- comissão;
- desconto válido;
- qualidade dos campos essenciais.

## Fora de escopo

- Gerar copy final.
- Publicar em WhatsApp, Telegram ou qualquer canal real.
- Converter link afiliado quando o link já vier convertido.
- Criar crawler amplo de marketplace.

## Critérios de aceite

- Dado produto sem preço, ele é removido ou bloqueado.
- Dado produto sem link, ele é removido ou bloqueado.
- Dado produto duplicado, apenas o vencedor segue no pipeline.
- Dado catálogo válido, a saída contém ofertas normalizadas.
- Nenhuma chamada real de HTTP acontece sem trava explícita.

## Testes esperados

- Teste para remoção de preço inválido.
- Teste para remoção de link ausente.
- Teste para marketplace desconhecido.
- Teste para deduplicação.
- Teste para preservação de campos válidos.

## Harness / validação local

Validação esperada no fluxo local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
```

O comando deve permanecer em dry-run e gerar artefatos locais em `.data/`.

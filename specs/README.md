# Specs

Este diretório contém contratos implementáveis do projeto.

## Como usar

- Cada spec deve ser revisada antes da implementação.
- Cada spec deve ter número sequencial de três dígitos.
- Não renumerar specs antigas.
- Não implementar comportamento fora do escopo da spec.
- Quando a implementação terminar, atualizar o status da spec.

## Ordem inicial de revisão

1. [`001_catalog_ingestion.md`](001_catalog_ingestion.md)
2. [`002_product_scoring.md`](002_product_scoring.md)
3. [`003_copywriter_agent.md`](003_copywriter_agent.md)
4. [`004_affiliate_link_converter.md`](004_affiliate_link_converter.md)
5. [`005_media_mapper.md`](005_media_mapper.md)
6. [`006_local_flow_orchestrator.md`](006_local_flow_orchestrator.md)

## Template mínimo

```md
# SPEC NNN — Título

Status: Rascunho

## Objetivo

## Contexto

## Entrada

## Saída

## Regras obrigatórias

## Fora de escopo

## Critérios de aceite

## Testes esperados

## Harness / validação local
```

## Fonte de regras

A regra oficial de numeração e locais fica em [`docs/regras-de-arquivos.md`](../docs/regras-de-arquivos.md).

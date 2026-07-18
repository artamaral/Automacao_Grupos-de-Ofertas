# Projeto

Esta pasta e o ponto central de leitura do projeto.

O foco atual e MVP: colocar a operacao minima para rodar com o catalogo ativo
do Supabase e disparo controlado pelo n8n.

## Ordem recomendada de leitura

1. [`01-visao-geral.md`](01-visao-geral.md)
2. [`02-arquitetura-alvo.md`](02-arquitetura-alvo.md)
3. [`06-proximas-etapas.md`](06-proximas-etapas.md)
4. [`../decisao-mvp-supabase-n8n.md`](../decisao-mvp-supabase-n8n.md)
5. [`../runbook-n8n.md`](../runbook-n8n.md)
6. [`../supabase-catalog-schema.md`](../supabase-catalog-schema.md)
7. [`../supabase-publication-events.md`](../supabase-publication-events.md)

## Fonte canonica

A decisao vigente e:

```text
Catalogo ativo no Supabase
  -> n8n consulta ranking
  -> n8n monta mensagem
  -> n8n envia para destinos em allowlist
  -> Supabase registra historico
```

Quando houver conflito entre documentos, prevalece
[`../decisao-mvp-supabase-n8n.md`](../decisao-mvp-supabase-n8n.md).

## Documentos de referencia

Documentos sobre Cloud Run, runner HTTP, Google Planilhas, JSON local,
providers fake, checklists Shopee e operacao n8n antiga permanecem como
referencia historica ou apoio tecnico. Eles nao definem a execucao diaria do
MVP.

Cloud Run nao e requisito do MVP. Ele pode voltar depois como evolucao para
reduzir logica no n8n ou centralizar execucao em Python.

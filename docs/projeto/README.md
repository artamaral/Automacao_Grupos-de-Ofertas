# Projeto

Esta pasta e o ponto central de leitura do projeto.

O foco atual e MVP: colocar a operacao minima para rodar com o catalogo ativo
do Supabase e disparo controlado pelo n8n.

## Ordem recomendada de leitura

1. [`01-visao-geral.md`](01-visao-geral.md)
2. [`02-arquitetura-alvo.md`](02-arquitetura-alvo.md)
3. [`03-google-planilhas.md`](03-google-planilhas.md)
4. [`04-contrato-n8n-whatsapp.md`](04-contrato-n8n-whatsapp.md)
5. [`05-migracao.md`](05-migracao.md)
6. [`06-proximas-etapas.md`](06-proximas-etapas.md)
7. [`07-catalogos-operacionais.md`](07-catalogos-operacionais.md)
8. [`08-spec-distribuicao-editorial-feminino.md`](08-spec-distribuicao-editorial-feminino.md)
9. [`09-spec-gerador-offline-posts-shopee.md`](09-spec-gerador-offline-posts-shopee.md)
10. [`../decisao-mvp-supabase-n8n.md`](../decisao-mvp-supabase-n8n.md)
11. [`../runbook-n8n.md`](../runbook-n8n.md)
12. [`../supabase-catalog-schema.md`](../supabase-catalog-schema.md)
13. [`../supabase-publication-events.md`](../supabase-publication-events.md)

## Specs aprovadas para evolucao

- [`08-spec-distribuicao-editorial-feminino.md`](08-spec-distribuicao-editorial-feminino.md)
  define a redistribuicao editorial do plano diario do perfil `feminino`.
- [`09-spec-gerador-offline-posts-shopee.md`](09-spec-gerador-offline-posts-shopee.md)
  define o gerador local de posts a partir de URL Shopee, sem publicacao automatica.

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

Planilha criada no Google Sheets:

- `Projeto Ofertas - Regras Operacionais (Google Sheets)`
- <https://docs.google.com/spreadsheets/d/16M0S-ipgQ9lOUqCtXTd1OC80I2emERCK8ByVllR06-E/edit?usp=drivesdk>

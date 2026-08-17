# Arquitetura alvo do MVP

## Decisao principal

O destino oficial do MVP e Supabase + n8n direto.

Isso significa:

- Supabase guarda o catalogo ativo, ranking, estado minimo e historico;
- n8n consulta o ranking diretamente no Supabase;
- n8n monta a mensagem por template simples;
- n8n executa o envio apenas para destinos em allowlist;
- n8n registra o resultado no Supabase;
- Cloud Run fica fora do caminho obrigatorio do MVP.

## Separacao de responsabilidades

### Repositorio

- migrations e contrato do Supabase;
- documentacao canonicamente curta;
- scripts de apoio para importar catalogos curados;
- referencias de templates e regras, quando uteis para versionamento.

### Ambiente local

- descoberta exploratoria;
- limpeza e curadoria dos catalogos;
- validacao dos CSVs;
- importacao controlada do catalogo curado no Supabase.

### Supabase

- `catalog_imports`;
- `catalog_items`;
- `offer_selection_state`;
- `v_offer_ranking_current`;
- `publication_events`.

### n8n

- agendamento ou gatilho manual da rodada;
- leitura de ofertas elegiveis no Supabase;
- aplicacao de limite por rodada;
- montagem de mensagens;
- bloqueio por allowlist;
- envio pelo canal configurado;
- registro do resultado em `publication_events`.

Hospedagem proposta:

- n8n self-hosted em VPS da Hostinger;
- manutencao pelo VSCode Remote SSH;
- credenciais configuradas no painel do n8n ou em arquivos locais da VPS fora
  do Git;
- workflow exportavel versionado no repositorio.

## Evolucoes futuras

As proximas camadas entram somente depois do MVP rodar:

- automatizar coleta e atualizacao do catalogo;
- revisar e melhorar nichos/subnichos;
- criar interface de aprovacao ou revisao;
- mover parte da logica do n8n para Cloud Run, se o workflow ficar pesado;
- ampliar roteamento por grupo;
- adicionar metricas de desempenho.

## Regra de leitura

Quando houver conflito, seguir
[`../decisao-mvp-supabase-n8n.md`](../decisao-mvp-supabase-n8n.md).

Documentos sobre Cloud Run, runner HTTP, n8n antigo, Google Planilhas e JSON
local sao referencia de transicao, nao arquitetura obrigatoria do MVP.

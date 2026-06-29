# Arquitetura alvo

## Decisao principal

O destino oficial do projeto passa a ser descoberta local com operacao em
Supabase e Cloud Run.

Isso significa:

- descoberta, limpeza e curadoria dependem de execucao local deliberada;
- a operacao diaria em nuvem nao depende do computador local ligado;
- somente catalogos curados e validados podem ser publicados no Supabase;
- ranking, estado, mensagens e auditoria ficam persistidos no Supabase;
- geracao e disparo de mensagens rodam no Cloud Run;
- agendamentos simples usam Cloud Scheduler.

## Separacao de responsabilidades

### Repositorio

- codigo Python
- testes
- contratos
- documentacao
- migrations e referencia das regras

### Ambiente local

- descoberta
- paginacao e inspecao da API
- limpeza e curadoria
- validacao dos catalogos
- publicacao controlada no Supabase

### Supabase

- catalogos operacionais publicados
- snapshots e rastreabilidade
- ranking e elegibilidade
- estado de selecao e cooldown
- mensagens e aprovacao
- historico de disparos

### Cloud Run

- geracao de mensagens
- compliance
- reivindicacao atomica de mensagens aprovadas
- disparo controlado por canal
- registro de sucesso ou falha

## Camadas legadas

Ainda existem no repositorio, mas nao fazem parte do fluxo oficial:

- `self-hosted/local`
- `cloud runner` HTTP
- `n8n cloud`
- Google Planilhas operacionais

Regra de leitura:

- nao usar essas camadas para novas implementacoes;
- manter os artefatos apenas como historico, apoio de debug e migracao;
- seguir [`../decisao-supabase-cloud-run.md`](../decisao-supabase-cloud-run.md)
  quando houver conflito.

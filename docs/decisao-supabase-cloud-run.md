# Decisao de arquitetura Supabase e Cloud Run

Este documento registra a arquitetura operacional atual do projeto.

Ele substitui a decisao que definia `n8n cloud` como ambiente operacional
principal.

## Decisao registrada

O caminho oficial passa a ser:

- descoberta e curadoria de catalogos executadas localmente;
- catalogo curado publicado no Supabase por um processo controlado;
- Supabase como fonte de verdade do catalogo operacional, estado, ranking,
  mensagens e historico de disparos;
- Cloud Run para geracao de mensagens e disparo controlado;
- Cloud Scheduler para acionar tarefas agendadas quando necessario;
- repositorio como fonte de codigo, migrations, contratos, testes e
  documentacao.

O `n8n` deixa de fazer parte da arquitetura alvo. Os artefatos e documentos de
`n8n` permanecem apenas como historico e apoio de transicao.

## Fronteira obrigatoria da descoberta

A descoberta permanece local.

Isso inclui:

- chamadas exploratorias para APIs de marketplace;
- paginacao ampla;
- inspecao de payloads;
- aplicacao e refinamento de taxonomias;
- limpeza e validacao de qualidade;
- revisao dos resultados por profile;
- geracao dos catalogos curados.

O fluxo em nuvem nao deve:

- executar descoberta ampla;
- decidir keywords exploratorias;
- refazer a limpeza completa dos catalogos;
- depender de acesso aos arquivos brutos locais;
- publicar automaticamente um catalogo que nao tenha sido validado.

Os catalogos locais validados continuam sendo a origem da publicacao:

```text
catalogs/clean/<profile>/clean_catalog_rating_4_8_plus.csv
```

O envio ao Supabase deve ser uma operacao explicita, auditavel e idempotente.
Cada importacao deve registrar ao menos:

- `profile`;
- versao ou identificador do catalogo;
- hash do arquivo;
- data da importacao;
- quantidade de linhas;
- origem local;
- resultado da validacao;
- usuario ou processo responsavel.

## Inicio do fluxo em nuvem

O fluxo operacional em nuvem comeca somente depois da publicacao do catalogo
curado:

```text
Descoberta local
  -> limpeza e validacao local
  -> catalogo curado
  -> importacao controlada no Supabase
  -> ranking e elegibilidade
  -> geracao de mensagens no Cloud Run
  -> compliance
  -> aprovacao humana
  -> disparo controlado no Cloud Run
  -> historico e auditoria no Supabase
```

## Responsabilidades do Supabase

O Supabase deve concentrar:

- catalogo operacional ativo por `profile`;
- snapshots necessarios para rastreabilidade;
- componentes e versao do score;
- view de ranking e elegibilidade;
- estado de selecao e cooldown;
- mensagens e seus status;
- aprovacao ou rejeicao humana;
- tentativas e resultados de disparo;
- grupos e destinos autorizados;
- logs operacionais sem segredos.

O score deve continuar explicavel. A view de ranking nao deve expor apenas um
numero final: ela deve preservar os componentes, motivos e versao da regra
aplicada.

## Responsabilidades do Cloud Run

O Cloud Run deve executar tarefas curtas e sem estado local duravel:

- ler ofertas elegiveis no Supabase;
- gerar mensagens;
- executar compliance;
- registrar mensagens pendentes de aprovacao;
- reivindicar mensagens aprovadas de forma atomica;
- disparar pelo provider permitido;
- registrar sucesso ou falha.

Uma unica imagem Python pode oferecer comandos separados, por exemplo:

- `generate`;
- `dispatch`.

Descoberta nao deve ser adicionada a essa imagem como responsabilidade do
runtime em nuvem.

## Seguranca e publicacao

Continuam obrigatorias:

- `dry-run` como padrao;
- nenhuma credencial no Git;
- segredos armazenados fora do repositorio;
- aprovacao humana antes de publicacao real;
- canal e grupo previamente autorizados;
- idempotencia para impedir mensagens duplicadas;
- logs de tentativa, sucesso e falha;
- bloqueio por configuracao explicita quando publicacao real nao estiver
  liberada.

## Papel dos artefatos atuais

- arquivos locais de descoberta e catalogos limpos continuam ativos;
- stores JSON continuam como apoio de desenvolvimento, testes e migracao;
- arquivos de `n8n` e Google Planilhas deixam de ser fonte final de verdade;
- `cloud runner` antigo permanece apenas como referencia de transicao;
- novas regras de negocio devem ser versionadas no repositorio e refletidas por
  migrations ou configuracao controlada no Supabase.

## Ordem de implementacao

1. definir schema e migrations do Supabase;
2. criar importacao idempotente do catalogo curado local;
3. criar view de ranking e elegibilidade;
4. migrar estado de selecao e cooldown;
5. conectar geracao de mensagens ao Supabase;
6. implementar launcher de mensagens no Cloud Run;
7. configurar Cloud Scheduler somente para os jobs realmente necessarios;
8. retirar o `n8n` do caminho operacional oficial.

As regras finas de score nao precisam ser redefinidas durante a criacao da
fundacao de dados.

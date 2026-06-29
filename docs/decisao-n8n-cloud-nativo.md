# Decisao de arquitetura n8n cloud nativo

Este documento consolida a decisao arquitetural atual do projeto para a
operacao com `n8n`.

Ele substitui qualquer leitura anterior que colocava `self-hosted/local` e
`hosted/cloud` como destinos equivalentes de medio prazo.

## Decisao registrada

O caminho oficial do projeto passa a ser:

- `n8n cloud` como ambiente operacional principal;
- dados operacionais da rodada mantidos no ecossistema do `n8n`;
- regras operacionais mantidas em Google Planilhas;
- catalogos operacionais disponiveis ao `n8n`;
- logs e estado da rodada persistidos em artefatos acessiveis pela automacao do
  `n8n`;
- fluxo sem dependencia de revisao humana obrigatoria no contrato default.

Leitura pratica:

- o repositorio continua sendo a fonte de codigo e contrato;
- a operacao diaria nao deve depender de PC local ligado;
- a operacao diaria nao deve depender de `self-hosted`;
- a operacao diaria nao deve depender de editar `toml`, `txt` ou `json`
  manualmente fora do `n8n`.

## O que foi descartado

As seguintes leituras deixam de ser alvo principal:

- `n8n self-hosted` como destino operacional definitivo;
- PC local ligado como requisito permanente da automacao;
- `cloud runner` HTTP como arquitetura final;
- arquivos locais em `config/*.toml` e `config/message_templates/*.txt` como
  fonte final de verdade operacional.

Esses elementos podem continuar existindo, mas com outro papel:

- `self-hosted/local` vira trilha de apoio, debug e transicao;
- `cloud runner` vira ponte tecnica temporaria;
- arquivos versionados em `config/` viram referencia de contrato e base de
  migracao.

## O que "tudo dentro do n8n" significa

Nesta decisao, "tudo dentro do n8n" significa que a operacao deve depender do
ecossistema do `n8n`, e nao do computador do operador.

Isso inclui:

- configuracoes operacionais;
- catalogos ativos por `profile`;
- artefatos de rodada;
- estado de selecao e cooldown;
- logs operacionais;
- roteamento por grupo;
- templates e cupons globais.

Isso nao significa mover o codigo-fonte versionado para dentro de uma planilha.

Separacao correta:

- repositorio: codigo, testes, contratos, documentacao, referencia de schema;
- n8n: execucao operacional, automacao, armazenamento acessivel ao workflow,
  observabilidade da rodada;
- Google Planilhas: regras editaveis pelo operador.

## Regras em Google Planilhas

Todos os arquivos de regras da operacao devem migrar para Google Planilhas.

Essa decisao vale para:

- descoberta;
- selecao;
- grupos;
- cupons;
- templates.

Abas ou planilhas logicas esperadas:

- `discovery_profiles`
- `selection_profiles`
- `group_profiles`
- `coupon_urls`
- `message_templates`

Motivos da decisao:

- reduzir atrito de manutencao;
- permitir alteracao operacional sem editar arquivo local;
- facilitar futura automacao de sincronizacao;
- deixar o modelo compativel com `n8n cloud`;
- evitar que a operacao dependa de pull, commit ou acesso ao filesystem local.

## Papel dos arquivos atuais em config

Os arquivos atuais continuam uteis, mas mudam de papel.

Eles passam a ser:

- referencia do contrato ja validado;
- base para migracao;
- fallback tecnico durante a transicao;
- material de teste e auditoria do comportamento esperado.

Eles deixam de ser:

- fonte final de verdade operacional;
- superficie principal de manutencao do operador.

## Catalogos, logs e estado

### Catalogos

Os catalogos operacionais devem estar acessiveis ao `n8n` sem depender do
workspace local do operador.

Direcao:

- um catalogo ativo por `profile`;
- atualizado por fluxo controlado;
- consumido diretamente pela rodada automatica.

Backlog associado:

- criar script local do operador para atualizar o catalogo operacional no
  ambiente do `n8n`.

### Logs e artefatos

Os artefatos da rodada continuam existindo, mas devem ser tratados como saida
operacional do `n8n`:

- `offers.json`
- `selection_state.json`
- `copy_briefs.json`
- `messages.json`
- `review_queue.json`
- `publication_manifest.json`
- `dispatch_artifact.json`
- `dispatch_report.json`

O ponto central e:

- a automacao precisa conseguir produzir, ler e usar esses artefatos sem
  depender do operador abrir a maquina local.

### Estado operacional

O estado por item continua necessario:

- `selected_at`
- `cooldown_until`
- `last_sent_at`
- `selection_count`

Mas a persistencia desse estado deve acompanhar a migracao para a operacao
nativa no `n8n`.

## Regra de volume e processamento

Esta fase consolidou outra decisao importante:

- o `n8n cloud` nao deve concentrar parse e score dos tres nichos no mesmo
  bloco pesado;
- o workflow nativo deve expandir a janela em items por `profile`;
- cada `profile` processa seu proprio catalogo, seu proprio score e sua propria
  selecao;
- a consolidacao entre nichos acontece so depois que os tres resultados
  unitarios existirem.

Implicacao pratica:

- a unidade de escala do workflow passa a ser `profile`;
- adicionar um novo nicho significa adicionar mais um item ao pipeline
  reutilizavel;
- nao significa aumentar um bloco central que tenta carregar todos os catalogos
  juntos.

## Revisao humana

A revisao humana deixa de ser obrigatoria no contrato minimo.

Leitura correta:

- `review_queue.json` pode continuar existindo;
- ele permanece como artefato tecnico e de auditoria;
- o fluxo default deve seguir automaticamente para `finalize`;
- gates manuais futuros sao extensoes operacionais, nao pre-requisito do
  pipeline principal.

## Implicacao para a arquitetura atual

Hoje o repositorio ainda tem duas trilhas:

- `self-hosted/local`
- `hosted/cloud` por HTTP

Mas, a partir desta decisao:

- a trilha `cloud/nativa` e o alvo oficial;
- a trilha `self-hosted/local` e apenas transitoria;
- nenhuma nova regra de negocio deve nascer acoplada ao modo local;
- qualquer avancao em um nicho deve nascer horizontalizada para todos os
  profiles e preparada para a arquitetura nativa.

## Ordem de prioridade daqui para frente

1. migrar regras operacionais para Google Planilhas;
2. modelar leitura dessas planilhas no fluxo do `n8n`;
3. mover catalogos e estado operacional para a superficie de dados usada pelo
   `n8n`;
4. estruturar o workflow nativo com processamento pesado por `profile`;
5. preservar o contrato dos artefatos finais;
6. usar a trilha local apenas como apoio enquanto a trilha nativa nao assume.

## Regra pragmatica de custo

Nao antecipar decisoes que gerem custo operacional desnecessario.

Portanto:

- dominio proprio nao e pre-requisito desta fase;
- hostname estavel pago nao e pre-requisito desta fase;
- qualquer infra adicional so entra quando houver necessidade real comprovada.

Essa diretriz vale especialmente para elementos que surgiram apenas para
viabilizar a ponte HTTP temporaria.

## Documento de referencia

Quando houver conflito entre documentos mais antigos e a leitura atual, esta
decisao deve prevalecer.

Documentos que devem ser lidos em conjunto com ela:

- [`docs/contrato-n8n-whatsapp.md`](contrato-n8n-whatsapp.md)
- [`docs/fluxo-operacional.md`](fluxo-operacional.md)
- [`docs/objetivo-operacional.md`](objetivo-operacional.md)
- [`docs/n8n-workflow.md`](n8n-workflow.md)
- [`docs/runbook-n8n.md`](runbook-n8n.md)

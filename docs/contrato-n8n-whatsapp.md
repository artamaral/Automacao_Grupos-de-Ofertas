# Contrato n8n e WhatsApp

Este documento registra o contrato operacional com `n8n`, a decisao de canal
real inicial e a distribuicao de responsabilidades entre repositorio e
orquestrador.

O passo a passo de implantacao esta em
[`docs/runbook-n8n.md`](runbook-n8n.md).

A decisao arquitetural consolidada da fase esta em
[`docs/decisao-n8n-cloud-nativo.md`](decisao-n8n-cloud-nativo.md).

A arquitetura recomendada para rodar multiplos nichos e grupos na mesma
execucao esta em
[`docs/n8n-arquitetura-multi-nicho.md`](n8n-arquitetura-multi-nicho.md).

## Decisao registrada

- o `n8n` sera o orquestrador externo do fluxo;
- os dados operacionais da rodada devem nascer e permanecer no `n8n` desde o
  inicio da integracao;
- os catalogos operacionais usados na rodada devem ficar disponiveis no `n8n`;
- os scripts chamados pelo operador e pela automacao devem ficar disponiveis no
  ambiente do `n8n`;
- a regra de negocio continua dentro do projeto;
- todos os arquivos de regras da operacao devem migrar para Google Planilhas,
  para que a manutencao operacional aconteca no proprio ambiente do `n8n` e
  possa ser automatizada depois por scripts de sincronizacao;
- o primeiro canal real alvo passa a ser `WhatsApp`;
- o envio real controlado deve acontecer no `n8n`, usando o artefato de
  dispatch gerado pelo projeto;
- o publisher Python continua em `dry-run`;
- a confirmacao de entrega real volta do `n8n` para o runner HTTP enquanto a
  trilha cloud nativa ainda nao assumir completamente a operacao.

## Distribuicao de responsabilidades

### Repositorio

O repositorio continua sendo a fonte de verdade para:

- codigo Python;
- contratos de artefato;
- configuracoes versionadas;
- templates;
- regras de score, selecao, compliance e manifesto;
- documentacao operacional.

### n8n

O `n8n` passa a ser o centro operacional para:

- armazenar os dados da rodada em execucao;
- armazenar ou referenciar os catalogos ativos usados na rodada;
- executar os scripts operacionais;
- manter o encadeamento da rodada;
- concentrar o estado observado pela operacao humana.

Regra pratica:

- o repositorio define como o fluxo funciona;
- o `n8n` concentra onde o fluxo roda e onde os dados operacionais ficam.

## Papel do n8n

O `n8n` pode:

- disparar a rodada por `profile`;
- manter os arquivos da rodada no proprio ambiente;
- manter os catalogos ativos no proprio ambiente;
- executar os scripts do fluxo no proprio ambiente;
- aguardar ou integrar a revisao humana;
- chamar a consolidacao dos artefatos aprovados;
- ler os artefatos finais para entrega externa;
- registrar sucesso, bloqueio e falha em sistema externo.

O `n8n` nao deve:

- recalcular score;
- aplicar banda por subnicho;
- decidir cooldown;
- montar copy;
- alterar manifesto manualmente;
- decidir compliance.

## Contrato operacional atual

O contrato atual do `n8n` usa apenas dois comandos:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --profile feminino
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize --profile feminino
```

A unica diferenca entre nichos deve ser `--profile`.

Na implantacao alvo, esses comandos devem rodar no ambiente do `n8n`, usando
paths locais do proprio `n8n` para dados e catalogos.

Perfis operacionais atuais:

- `feminino`
- `mae-e-bebe`
- `auto-e-moto`

## Etapa 1: prepare

Entrada logica:

- `profile`

Entradas resolvidas por configuracao:

- Google Planilha `discovery_profiles`
- Google Planilha `selection_profiles`
- Google Planilha `group_profiles`
- Google Planilha `coupon_urls`
- Google Planilha `message_templates`
- catalogo ativo do `profile`, armazenado no ambiente do `n8n`
- estado operacional do `profile`, armazenado no ambiente do `n8n`

Saidas produzidas:

- `offers.json`
- `selection_state.json`
- `copy_briefs.json`
- `messages.json`
- `messages.txt`
- `messages_preview.html`
- `review_queue.json`
- `review_plan.json`
- `review_plan.txt`

Responsabilidade desta etapa:

- coletar do catalogo curado;
- aplicar score;
- aplicar gate de selecao;
- revalidar refresh final quando habilitado;
- gerar copy por template estatico;
- validar compliance;
- montar fila de revisao.

Nenhum envio acontece aqui.

Recomendacao de path no `n8n`:

```text
<n8n-data>/<profile>/offers.json
<n8n-data>/<profile>/selection_state.json
<n8n-data>/<profile>/copy_briefs.json
<n8n-data>/<profile>/messages.json
<n8n-data>/<profile>/messages_preview.html
<n8n-data>/<profile>/review_queue.json
```

## Etapa 2: revisao

Arquivo fonte da revisao:

- `review_queue.json` no ambiente do `n8n`

Status esperados por item:

- `pending`
- `approved`
- `rejected`

No estado atual, a mudanca de status deve continuar sendo feita pelo fluxo do
projeto. O caminho recomendado e chamar as ferramentas de revisao do proprio
repositorio, e nao editar JSON manualmente.

## Etapa 3: finalize

Entrada principal:

- `review_queue.json` no ambiente do `n8n`

Saidas produzidas:

- `approved_messages.json`
- `approved_messages.txt`
- `approved_messages_by_group/`
- `publication_manifest.json`
- `dispatch_artifact.json`
- `dispatch_report.json`
- `dispatch_report.txt`
- `local_review_bundle.json`

Efeito adicional:

- atualiza `last_sent_at` em `selection_state.json` para os
  drafts presentes no `dispatch_artifact.json`

## Artefato que o n8n deve consumir

O artefato principal de entrega para o proprio orquestrador e:

- `dispatch_artifact.json` no ambiente do `n8n`

Ele ja sai agrupado por destino e adaptador de canal, com:

- `target`
- `adapter_kind`
- `status`
- `available_message_count`
- `selected_message_count`
- `skipped_message_count`
- `quiet_period_active`
- `blocked_reason`
- `selection_reason`
- `messages[]`

Cada mensagem ja contem:

- identificacao no manifesto;
- horario planejado;
- texto final;
- resumo da oferta;
- destino logico.

O artefato de confirmacao local e:

- `dispatch_report.json`

## Catalogos no n8n

Decisao desta etapa:

- os catalogos usados operacionalmente devem estar no `n8n` desde o inicio;
- a rodada nao deve depender do operador copiar manualmente um CSV para dentro
  do workspace do repositorio antes de cada execucao;
- o `n8n` deve manter um caminho por `profile` para o catalogo ativo.

Estrutura recomendada:

```text
<n8n-catalogs>/feminino/clean_catalog_rating_4_8_plus.csv
<n8n-catalogs>/mae-e-bebe/clean_catalog_rating_4_8_plus.csv
<n8n-catalogs>/auto-e-moto/clean_catalog_rating_4_8_plus.csv
```

## Scripts no n8n

Decisao desta etapa:

- os scripts operacionais tambem devem ficar disponiveis no ambiente do `n8n`
  desde o inicio;
- o operador nao deve depender de uma execucao manual paralela fora do `n8n`
  para rodar a esteira principal.

Isso nao elimina o repositorio como fonte de codigo. Significa apenas que a
instancia operacional do fluxo, chamada pela automacao, deve existir dentro do
ambiente em que o `n8n` roda.

## Regras em Google Planilhas

Decisao registrada desta fase:

- os arquivos de regras nao devem ter `toml` ou `txt` como formato final de
  operacao;
- a fonte de verdade operacional das regras deve ser Google Planilhas;
- isso vale para descoberta, selecao, grupos, cupons e templates;
- o objetivo e permitir manutencao simples pelo operador e futura automacao de
  alteracoes sem editar arquivos locais do repo.

Leitura correta do estado atual:

- os arquivos em `config/` continuam servindo como referencia do contrato ja
  validado;
- eles passam a ser base de migracao, nao o destino final da operacao nativa no
  `n8n`.

## Contrato atual para WhatsApp

No desenho atual, `WhatsApp` entra por `channel_adapter = "whatsapp"` em:

- `config/group_profiles.toml`
- `publication_manifest.json`
- `dispatch_artifact.json`

Hoje isso significa:

- roteamento para destino logico de WhatsApp;
- validacao de limites e quiet period;
- geracao de `dispatch_artifact.json`;
- entrega real feita no `n8n` para um grupo controlado;
- confirmacao externa de entrega via runner HTTP.

O que continua fora do Python:

- sessao conectada;
- credencial do provedor;
- envio real do canal;
- retry e reconciliacao do provedor.

## Bloco de implementacao que vem agora

Para iniciar o caminho de `WhatsApp` sem romper a seguranca, o bloco atual de
implementacao passa a ser:

1. `n8n` chama o runner HTTP para `prepare` e `finalize`;
2. `n8n` carrega as `deliveries[]` do `dispatch-window` ou `run-window`;
3. `n8n` envia no provedor real apenas para os destinos permitidos do teste;
4. a cada sucesso, `n8n` chama `confirm-delivery`;
5. o runner atualiza `last_sent_at` apenas das mensagens realmente enviadas;
6. o publisher Python continua em `dry-run` como camada local de validacao;
7. a expansao para mais grupos continua dependente de allowlist e checklist.

Regra pragmatica desta fase:

- nao introduzir custo de dominio, hostname estavel ou infra adicional antes de
  validar o resultado operacional;
- `Quick Tunnel` ou mecanismo equivalente continuam suficientes para a etapa de
  prova controlada da ponte HTTP;
- a decisao de URL estavel fica adiada ate existir necessidade real de
  repeticao e escala.

## Regra obrigatoria

Enquanto o publisher real de `WhatsApp` dentro do Python nao existir e nao for
validado:

- `dispatch_execute_cli` continua em `dry-run`;
- `ENABLE_REAL_PUBLISH` continua `false` no projeto Python;
- o envio real permitido nesta fase deve acontecer apenas no `n8n`;
- o `n8n` so deve enviar para destinos explicitamente allowlisted;
- a confirmacao de entrega deve voltar ao runner por `confirm-delivery` ou
  `confirm-window-deliveries`.

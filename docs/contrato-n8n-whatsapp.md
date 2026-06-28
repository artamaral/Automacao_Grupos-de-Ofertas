# Contrato n8n e WhatsApp

Este documento registra o contrato operacional com `n8n`, a decisao de canal
real inicial e a distribuicao de responsabilidades entre repositorio e
orquestrador.

O passo a passo de implantacao esta em
[`docs/runbook-n8n.md`](runbook-n8n.md).

## Decisao registrada

- o `n8n` sera o orquestrador externo do fluxo;
- os dados operacionais da rodada devem nascer e permanecer no `n8n` desde o
  inicio da integracao;
- os catalogos operacionais usados na rodada devem ficar disponiveis no `n8n`;
- os scripts chamados pelo operador e pela automacao devem ficar disponiveis no
  ambiente do `n8n`;
- a regra de negocio continua dentro do projeto;
- o primeiro canal real alvo passa a ser `WhatsApp`;
- enquanto o publisher real nao existir, o fluxo continua estritamente em
  `dry-run`.

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

- `config/discovery_profiles.toml`
- `config/selection_profiles.toml`
- `config/group_profiles.toml`
- `config/coupon_urls.toml`
- `config/message_templates/shopee.txt`
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

## Contrato atual para WhatsApp

No desenho atual, `WhatsApp` entra por `channel_adapter = "whatsapp"` em:

- `config/group_profiles.toml`
- `publication_manifest.json`
- `dispatch_artifact.json`

Hoje isso ainda significa:

- roteamento para destino logico de WhatsApp;
- validacao de limites e quiet period;
- simulacao local de disparo.

Ainda nao significa:

- sessao conectada;
- envio real;
- integracao oficial com provedor;
- confirmacao de entrega externa.

## Bloco de implementacao que vem agora

Para iniciar o caminho de `WhatsApp` sem romper a seguranca, o proximo bloco
de desenvolvimento deve ser:

1. preparar a estrutura de dados, scripts e catalogos no ambiente do `n8n`;
2. adaptar os comandos do fluxo para usar paths operacionais do `n8n`;
3. manter `n8n` executando `prepare` e `finalize` sobre seus proprios arquivos;
4. criar a camada de `WhatsAppPublisher` por interface isolada;
5. manter fallback em `dry-run`;
6. registrar resultado por mensagem em formato auditavel;
7. liberar `ENABLE_REAL_PUBLISH=true` somente depois do checklist completo.

## Regra obrigatoria

Enquanto o publisher real de `WhatsApp` nao existir e nao for validado:

- `dispatch_execute_cli` continua em `dry-run`;
- `ENABLE_REAL_PUBLISH` continua `false`;
- o `n8n` pode orquestrar a rodada, mas nao deve assumir entrega real.

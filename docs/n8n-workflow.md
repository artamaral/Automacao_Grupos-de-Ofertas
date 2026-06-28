# Workflow n8n

Este documento registra o estado atual das trilhas de integracao com `n8n`.

Leitura correta da fase:

- alvo oficial: `n8n cloud` com operacao nativa;
- ponte tecnica atual: `hosted/cloud` por HTTP;
- trilha de apoio/transicao: `self-hosted/local`.

A decisao consolidada esta em
[`docs/decisao-n8n-cloud-nativo.md`](decisao-n8n-cloud-nativo.md).

Documentos relacionados:

- [`docs/runbook-n8n.md`](runbook-n8n.md)
- [`docs/n8n-workflow-implementavel.md`](n8n-workflow-implementavel.md)
- [`docs/n8n-cloud-runner.md`](n8n-cloud-runner.md)

## Decisao operacional atual

O fluxo principal nao possui mais validacao humana obrigatoria.

Leitura correta nesta fase:

- `review_queue.json` continua existindo;
- ele e um artefato tecnico de auditoria e roteamento;
- o fluxo default segue automaticamente para `finalize`;
- aprovacao manual futura sera extensao opcional, nao contrato minimo.

## Trilha 1: self-hosted/local

Arquivo:

- [`n8n/workflows/ofertas-rodada-self-hosted-skeleton.json`](../n8n/workflows/ofertas-rodada-self-hosted-skeleton.json)

Uso recomendado:

- `n8n` com acesso ao host
- possibilidade de usar nodes de comando do sistema
- projeto montado no mesmo ambiente do `n8n`

Caracteristicas:

- chama scripts PowerShell do projeto;
- usa filesystem local diretamente;
- continua existindo como apoio de transicao e debug;
- nao e mais o destino arquitetural do projeto.

## Trilha 2: hosted/cloud por HTTP

Arquivo:

- [`n8n/workflows/ofertas-rodada-skeleton.json`](../n8n/workflows/ofertas-rodada-skeleton.json)

Uso recomendado:

- `n8n` hospedado
- ambiente sem `Execute Command`
- necessidade de operacao autonoma por HTTP

Caracteristicas:

- nao executa scripts locais dentro do `n8n`;
- chama o `cloud runner` por HTTP;
- preserva o mesmo contrato de `prepare/finalize`;
- funciona como ponte para a operacao cloud enquanto a versao nativa no `n8n`
  nao absorve regras, catalogos, estado e logs.

## Contrato minimo comum

As duas trilhas devem produzir a mesma ideia operacional:

```text
catalogo ativo -> prepare -> artefatos -> finalize -> dispatch_artifact
```

Artefatos minimos do `prepare`:

- `offers.json`
- `selection_state.json`
- `copy_briefs.json`
- `messages_preview.html`
- `review_queue.json`

Artefatos minimos do `finalize`:

- `approved_messages.json`
- `publication_manifest.json`
- `dispatch_artifact.json`
- `dispatch_report.json`

## Desenho logico da trilha hosted/cloud

```text
Trigger
  -> Set Contexto Base
  -> Validar Contexto
  -> GET /health
  -> POST /prepare-window
  -> POST /finalize-window
  -> POST /dispatch-window
  -> envio real no n8n
  -> POST /confirm-delivery
  -> Montar resumo da rodada
  -> Persistir log
  -> Notificar conclusao
```

## Desenho logico da trilha self-hosted/local

```text
Trigger
  -> Expandir profiles
  -> Validar profile
  -> Validar catalogo local
  -> Executar prepare local
  -> Validar artefatos
  -> Executar finalize local
  -> Validar artefatos finais
  -> Consolidar resumo
```

## Perfis permitidos

- `feminino`
- `mae-e-bebe`
- `auto-e-moto`

## Regra de horizontalizacao

Toda evolucao do fluxo operacional deve obedecer a esta regra:

- se a mudanca afeta o contrato principal, ela deve ficar refletida nas duas trilhas;
- a diferenca aceitavel entre elas e apenas o meio de execucao:
  - local por comando
  - cloud por HTTP
- a selecao, copy, compliance tecnico e saida final devem continuar equivalentes.

## Resultado esperado desta fase

Ao final desta fase o repositorio passa a ter:

- uma trilha `self-hosted/local` preservada apenas como apoio;
- uma ponte `hosted/cloud` funcional para validacao controlada;
- a documentacao apontando `n8n cloud` nativo como destino principal;
- nenhuma dependencia de revisao humana no contrato default.

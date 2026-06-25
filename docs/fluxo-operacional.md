# Fluxo operacional local

Este projeto deve ser operado por automação, agendador ou orquestrador. O objetivo é evitar execução manual de vários scripts pequenos.

## Comando principal

Use o orquestrador local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --profile beleza
```

Fluxo recomendado para operação recorrente:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile beleza
```

O perfil deve ser mantido em [`config/discovery_profiles.toml`](../config/discovery_profiles.toml)
e está documentado em [`docs/discovery-profiles.md`](discovery-profiles.md).

Os grupos de destino devem ser mantidos em [`config/group_profiles.toml`](../config/group_profiles.toml)
e estão descritos em [`docs/group-profiles.md`](group-profiles.md).

Quando a meta for aprender com a saída da coleta, o caminho recomendado é salvar
também a inspeção estruturada:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile beleza --save-inspection-json .\tmp\beleza-inspection.json
```

Esse artefato deve ser usado para observar a saída real por `profile` antes de
endurecer classificação, roteamento e score.

Após a aprovação/rejeição da fila por um processo humano ou interface externa, finalize os artefatos locais:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize
```

Se o pacote foi instalado na venv, os atalhos equivalentes são:

```powershell
ofertas-local-flow --stage prepare --profile beleza
ofertas-local-flow --stage finalize
```

## Caminhos padrão

O fluxo usa `.data` por padrão:

```text
.data/offers.json
.data/messages.json
.data/messages.txt
.data/review_queue.json
.data/review_plan.json
.data/review_plan.txt
.data/approved_messages.json
.data/approved_messages.txt
.data/approved_messages_by_group/
.data/dispatch_artifact.json
.data/dispatch_report.json
.data/publication_manifest.json
.data/local_review_bundle.json
```

## Etapa prepare

A etapa `prepare`:

- coleta ofertas em modo seguro;
- pontua ofertas;
- gera mensagens;
- valida compliance;
- salva artefatos locais;
- cria fila de revisão pendente já roteada pelo catálogo de grupos quando houver correspondência;
- gera `review_plan.json` e `review_plan.txt` com grupos elegíveis, bloqueios e mensagens previstas por grupo;
- não envia nada;
- não chama publicação real.

## Etapa finalize

A etapa `finalize`:

- aplica gate da fila;
- exporta somente aprovadas;
- separa aprovadas por grupo em artefatos prontos para operacao;
- cria manifesto local usando o destino roteado em cada item aprovado da fila;
- valida manifesto;
- gera artefato de disparo agrupado por destino, ainda sem envio real;
- executa o artefato em dry-run e salva relatório por destino;
- cria bundle local de auditoria;
- executa doctor local;
- para na primeira falha;
- não envia nada;
- não chama publicação real.

Dentro de `.data/approved_messages_by_group/`, cada grupo gera um par de arquivos
`<group-slug>.json` e `<group-slug>.txt`, mantendo o destino da revisão já pronto
para uso posterior no disparo.

O arquivo `.data/dispatch_artifact.json` consolida as mensagens prontas por
`target`, junto com o `adapter_kind` configurado por grupo, servindo como contrato de entrada para um futuro disparador local ou
automatizado.

O arquivo `.data/dispatch_report.json` registra a simulação da rodada de
disparo, por destino e por mensagem, sem qualquer envio real.

No estado atual, o executor de disparo trabalha com adaptadores `dry-run` de
canal. O adaptador de cada destino passa a ser definido no catálogo de grupos,
e os adaptadores `whatsapp`, `telegram` e `console` permanecem disponíveis para
simulação e testes.

## Papel humano

O humano não deve operar vários CLIs manualmente no fluxo principal.

O humano participa apenas para:

- aprovar ou rejeitar mensagens;
- configurar credenciais;
- liberar travas de segurança quando for apropriado;
- validar localmente quando solicitado.

## Ferramentas auxiliares

Os CLIs menores existentes permanecem úteis para debug, auditoria e manutenção, mas não devem ser o caminho operacional principal.

Exemplos:

```text
ofertas-review-list
ofertas-review-decide
ofertas-review-export
ofertas-review-gate
ofertas-manifest-validate
ofertas-local-doctor
```

Na revisão humana, o item deve ser avaliado já com o contexto de `group`, `destination_ref`
e tom configurado no catálogo operacional, para reduzir decisão solta fora da configuração.

## Validação de desenvolvimento

Após mudanças no código:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

No Windows PowerShell, se a saída do fluxo falhar por encoding ao imprimir
textos acentuados ou símbolos da mensagem, habilite UTF-8 antes de rodar o
comando:

```powershell
$env:PYTHONUTF8='1'
```

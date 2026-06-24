# Fluxo operacional local

Este projeto deve ser operado por automação, agendador ou orquestrador. O objetivo é evitar execução manual de vários scripts pequenos.

## Comando principal

Use o orquestrador local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
```

Fluxo recomendado para operação recorrente:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile beleza
```

O perfil deve ser mantido em [`config/discovery_profiles.toml`](../config/discovery_profiles.toml)
e está documentado em [`docs/discovery-profiles.md`](discovery-profiles.md).

Quando a meta for aprender com a saída da coleta, o caminho recomendado é salvar
também a inspeção estruturada:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile beleza --save-inspection-json .\tmp\beleza-inspection.json
```

Esse artefato deve ser usado para observar a saída real por `profile` antes de
endurecer classificação, roteamento e score.

Após a aprovação/rejeição da fila por um processo humano ou interface externa, finalize os artefatos locais:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize --target grupo-maquiagem
```

Se o pacote foi instalado na venv, os atalhos equivalentes são:

```powershell
ofertas-local-flow --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
ofertas-local-flow --stage finalize --target grupo-maquiagem
```

## Caminhos padrão

O fluxo usa `.data` por padrão:

```text
.data/offers.json
.data/messages.json
.data/messages.txt
.data/review_queue.json
.data/approved_messages.json
.data/approved_messages.txt
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
- cria fila de revisão pendente;
- não envia nada;
- não chama publicação real.

## Etapa finalize

A etapa `finalize`:

- aplica gate da fila;
- exporta somente aprovadas;
- cria manifesto local;
- valida manifesto;
- cria bundle local de auditoria;
- executa doctor local;
- para na primeira falha;
- não envia nada;
- não chama publicação real.

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

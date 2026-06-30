# SPEC 006 — Orquestrador Local do Fluxo Principal

Status: Rascunho

## Objetivo

Definir o contrato do fluxo operacional local que prepara fila de revisão, consolida mensagens aprovadas e mantém o projeto simples para operação diária.

## Contexto

O README já define o orquestrador local como caminho recomendado. Esta spec consolida o comportamento esperado para futuras mudanças nesse fluxo.

## Entrada

Parâmetros operacionais mínimos:

```text
stage
niche
marketplace
target
```

Estágios esperados:

```text
prepare
finalize
```

## Saída

Artefatos locais em `.data/`.

Exemplos:

```text
.data/review_queue.json
.data/approved_messages.json
.data/publication_manifest.json
.data/local_review_bundle.json
```

## Regras obrigatórias

- O fluxo padrão não publica mensagens.
- O fluxo padrão não chama HTTP real.
- O fluxo deve parar na primeira falha relevante.
- O fluxo deve gerar artefatos auditáveis.
- O estágio `finalize` deve depender de aprovação/rejeição prévia.
- O comando principal deve evitar exigir vários CLIs pequenos do usuário.
- Saídas devem ser claras para execução local no Windows PowerShell.

## Stage `prepare`

Responsável por:

- carregar ofertas;
- ranquear;
- gerar copy;
- validar compliance;
- montar fila de revisão.

## Stage `finalize`

Responsável por:

- ler fila revisada;
- consolidar aprovadas;
- gerar manifesto/bundle local;
- não publicar em canal real.

## Fora de escopo

- Publicação real.
- Ativação automática de HTTP real.
- Edição manual de `.env`.
- Substituição da revisão humana.

## Critérios de aceite

- `prepare` gera fila de revisão local.
- `finalize` consolida apenas mensagens aprovadas.
- Com travas desligadas, não há publicação real nem HTTP real.
- O comando funciona com marketplace `mock`.
- Erros são visíveis e não silenciosos.

## Testes esperados

- Teste do stage `prepare`.
- Teste do stage `finalize` com aprovadas.
- Teste do stage `finalize` sem aprovações.
- Teste de bloqueio de publicação real por padrão.
- Teste de caminhos `.data`.

## Harness / validação local

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize --target grupo-maquiagem
```

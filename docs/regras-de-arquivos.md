# Regras de Arquivos, Numeração e Locais

Este documento define onde novos arquivos devem ser criados no repositório e como numerar documentos implementáveis.

## Objetivo

Evitar arquivos soltos, nomes inconsistentes e perda de contexto entre GPT, Codex, revisão humana e implementação local.

## Regra principal

Cada arquivo novo deve ter um motivo claro e um local previsível.

Antes de criar um arquivo, responder:

1. Este arquivo é documentação permanente, spec implementável, código, teste, fixture ou artefato local?
2. Ele precisa ser versionado?
3. Ele substitui algum documento existente?
4. Ele precisa de número sequencial?
5. Quem deve ler este arquivo: humano, GPT, Codex ou pipeline?

## Locais oficiais

### Raiz do repositório

Usar apenas para arquivos de entrada do projeto e configuração geral.

```text
AGENTS.md
README.md
pyproject.toml
.env.example
.gitignore
```

Não colocar specs, rascunhos, payloads, mídia ou artefatos operacionais na raiz.

### `docs/`

Documentação permanente e políticas do projeto.

Exemplos:

```text
docs/architecture.md
docs/catalog-quality.md
docs/copy-guidelines.md
docs/affiliate-compliance.md
docs/whatsapp-posting-policy.md
docs/media-guidelines.md
docs/regras-de-arquivos.md
```

Use `docs/` para explicar decisões, políticas, padrões e funcionamento esperado.

### `specs/`

Contratos implementáveis e revisáveis, sempre numerados.

Formato obrigatório:

```text
specs/NNN_nome_curto.md
```

Exemplos:

```text
specs/001_catalog_ingestion.md
specs/002_product_scoring.md
specs/003_copywriter_agent.md
```

### `src/ofertas_bot/`

Código de produção do projeto.

Organização esperada:

```text
src/ofertas_bot/agents/
src/ofertas_bot/providers/
src/ofertas_bot/models.py
src/ofertas_bot/settings.py
```

### `tests/`

Testes automatizados. Sempre que possível, espelhar o módulo testado.

Exemplos:

```text
tests/test_copywriter.py
tests/test_scorer.py
tests/test_local_flow_cli.py
```

### `.data/`

Artefatos locais de execução, revisão, fila, bundle e mídia. Não deve ser versionado como documentação permanente.

Exemplos:

```text
.data/review_queue.json
.data/approved_messages.json
.data/publication_manifest.json
.data/local_review_bundle.json
.data/media/
```

### `docs/decisions/`

Usar apenas se o projeto passar a registrar decisões arquiteturais formais.

Formato recomendado:

```text
docs/decisions/ADR-0001-nome-da-decisao.md
```

Não criar ADR para decisão pequena de implementação.

## Numeração de specs

### Formato

```text
NNN_nome_curto.md
```

- `NNN`: número sequencial com três dígitos.
- `nome_curto`: minúsculo, sem acento, separado por `_`.
- extensão sempre `.md`.

Exemplos válidos:

```text
001_catalog_ingestion.md
002_product_scoring.md
003_copywriter_agent.md
```

Exemplos inválidos:

```text
1 Catalogo.md
spec catalogo.md
catalogo-final-v2.md
003-Copywriter.md
```

### Sequência

- Começar em `001`.
- Usar sempre o próximo número disponível.
- Nunca renumerar specs antigas depois de criadas.
- Não reutilizar número de spec removida ou abandonada.
- Se uma spec for substituída, manter o arquivo e marcar status como `Substituída`.

## Status obrigatório em specs

Toda spec deve ter um campo `Status`.

Valores recomendados:

```text
Rascunho
Em revisão
Aprovada
Em implementação
Implementada
Substituída
Cancelada
```

## Template mínimo de spec

```md
# SPEC NNN — Título

Status: Rascunho

## Objetivo

## Contexto

## Entrada

## Saída

## Regras obrigatórias

## Fora de escopo

## Critérios de aceite

## Testes esperados

## Harness / validação local
```

## Quando atualizar `AGENTS.md`

Atualizar `AGENTS.md` quando a regra impactar diretamente como o GPT/Codex deve trabalhar.

Exemplos:

- fluxo obrigatório de implementação;
- comando de teste obrigatório;
- travas de segurança;
- regra para branch/commit;
- mudança no fluxo operacional principal.

## Quando atualizar `README.md`

Atualizar `README.md` quando a mudança impactar a entrada de um humano no projeto.

Exemplos:

- novo fluxo recomendado;
- nova documentação importante;
- novo comando principal;
- mudança de instalação;
- mudança de estrutura do projeto.

## Quando atualizar `docs/`

Atualizar `docs/` quando a mudança for regra, política, contexto ou explicação permanente.

## Quando criar spec

Criar spec quando existir mudança implementável que precise ser revisada antes do código.

Exemplos:

- novo comportamento no pipeline;
- novo provider;
- nova regra de scoring;
- nova validação de compliance;
- novo formato de catálogo;
- novo artefato de saída.

## Regra para revisão um por um

Quando um conjunto de specs for criado para revisão futura, cada spec deve ser independente. A revisão de uma não deve exigir aprovação automática das outras.

A ordem padrão de revisão é a ordem numérica.

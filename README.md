# Automação de Grupos de Ofertas

Projeto em **Python** para curadoria, pontuação e publicação controlada de ofertas de afiliados para grupos opt-in.

A versão atual usa um **fluxo local dry-run**: busca ofertas mockadas ou providers com transport fake injetável, pontua, gera copy, valida compliance e prepara artefatos locais sem enviar nada para WhatsApp real.

## Princípios

- Somente grupos com entrada voluntária e consentimento claro.
- Publicação real desabilitada por padrão.
- HTTP real desabilitado por padrão.
- Nenhum segredo versionado.
- Integrações externas isoladas atrás de providers.
- Nada de automação para burlar políticas, limites ou detecção de plataformas.

## Requisitos

- Python 3.11+
- `pip`

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
```

No Windows PowerShell, use sempre o Python da venv para evitar `pip` global apontando para outra versão:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

## Configuração

Copie o arquivo de exemplo e preencha apenas o `.env` local:

```powershell
Copy-Item .env.example .env
```

As travas devem permanecer desligadas por padrão:

```text
ENABLE_REAL_HTTP=false
ENABLE_REAL_PUBLISH=false
```

Mais detalhes em [`docs/environment.md`](docs/environment.md).

## Fluxo operacional recomendado

O caminho principal é o orquestrador local. Ele usa caminhos padrão em `.data` e reduz a necessidade de chamar vários scripts manualmente.

Etapa 1: preparar fila e artefatos locais:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
```

Etapa 2: depois que a fila for aprovada/rejeitada por processo humano ou interface externa, consolidar os artefatos finais:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize --target grupo-maquiagem
```

Após instalação na venv, o atalho equivalente é:

```powershell
ofertas-local-flow --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
ofertas-local-flow --stage finalize --target grupo-maquiagem
```

O fluxo operacional local:

- não envia mensagens;
- não chama publicação real;
- grava artefatos em `.data`;
- para na primeira falha;
- aplica gate antes de consolidar aprovadas;
- gera bundle local auditável.

## Ferramentas auxiliares

Os comandos menores continuam disponíveis para debug, auditoria e manutenção, mas não são o caminho operacional principal.

Exemplos:

```powershell
ofertas-review-list --queue-json .data\review_queue.json
ofertas-review-summary --queue-json .data\review_queue.json
ofertas-review-decide --queue-json .data\review_queue.json --item 1 --status approved --reviewer Arthur --notes "ok para teste"
ofertas-local-doctor --queue-json .data\review_queue.json --approved-json .data\approved_messages.json --manifest-json .data\publication_manifest.json --bundle-json .data\local_review_bundle.json
```

Detalhes em [`docs/fluxo-operacional.md`](docs/fluxo-operacional.md).

## Testes

```bash
python -m ruff check .
python -m pytest
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

## Documentação

- [`docs/fluxo-operacional.md`](docs/fluxo-operacional.md): fluxo operacional local simplificado.
- [`docs/environment.md`](docs/environment.md): variáveis de ambiente e execução local segura.
- [`docs/provider-fake-flow.md`](docs/provider-fake-flow.md): fluxo fake/injetável dos providers.
- [`docs/production-checklist.md`](docs/production-checklist.md): checklist antes de chamadas reais ou publicação real.
- [`docs/status-implantacao.md`](docs/status-implantacao.md): status atual da implantação e backlog.
- [`docs/status-integracao-shopee.md`](docs/status-integracao-shopee.md): ponto de retomada da integração Shopee.
- [`docs/cli-messages.md`](docs/cli-messages.md): padrão de mensagens do CLI.
- [`docs/copy-guidelines.md`](docs/copy-guidelines.md): diretrizes de copy.
- [`docs/commit-pattern.md`](docs/commit-pattern.md): padrão de commits.
- [`docs/ci.md`](docs/ci.md): validação automática com GitHub Actions.

## Estrutura

```text
src/ofertas_bot/
  agents/        # agentes funcionais do pipeline
  providers/     # integrações Shopee, Amazon, transport e mappers
  harness.py     # CLI de simulação
  models.py      # modelos de domínio
  settings.py    # configuração via ambiente
tests/
docs/
```

## Estado dos providers

- Mock: funcional para testes de ponta a ponta.
- Shopee: provider, gateway, builder, mapper, validações e captura anonimizada implementados; retomada real depende da aprovação da conta/app. Ver `docs/status-integracao-shopee.md`.
- Amazon: provider, gateway, builder, mapper e transport fake injetável implementados; chamada real não ativada.

## Roadmap

1. Base Python dry-run com mocks. Concluído.
2. Providers Shopee e Amazon com fluxo fake/injetável. Concluído.
3. Status de retomada da integração Shopee. Concluído.
4. Fluxo operacional local simplificado. Em andamento.
5. Persistência SQLite para histórico.
6. Fixtures anonimizadas com payloads reais.
7. Assinatura real da Amazon PA API.
8. Configuração controlada para HTTP real.
9. Publicação controlada em canal permitido e auditável.

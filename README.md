# Automação de Grupos de Ofertas

Projeto em **Python** para curadoria, pontuação e publicação controlada de ofertas de afiliados para grupos opt-in.

A versão atual usa um **harness dry-run**: busca ofertas mockadas ou providers com transport fake injetável, pontua, gera copy, valida compliance e simula a publicação sem enviar nada para WhatsApp real.

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

## Rodar o harness com segurança

Caminho recomendado para testar o pipeline completo:

```bash
python -m ofertas_bot.harness --niche maquiagem --marketplace mock --dry-run
```

No Windows PowerShell, usando o Python da venv:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --niche maquiagem --marketplace mock --dry-run
```

Também é possível salvar as mensagens aprovadas pelo compliance para revisão humana local, sem publicar nada real:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --niche maquiagem --marketplace mock --limit 1 --save-messages-json .data\messages.json --save-messages-text .data\messages.txt --save-review-queue-json .data\review_queue.json
```

Use o JSON de mensagens para auditoria técnica, o TXT para leitura/revisão manual e a fila `review_queue.json` para controlar quais mensagens continuam pendentes, aprovadas ou rejeitadas antes de qualquer etapa de publicação.

Para listar a fila local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.review_queue_list_cli --queue-json .data\review_queue.json
```

Para ver o resumo da fila local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.review_queue_summary_cli --queue-json .data\review_queue.json
```

Para marcar uma decisão humana na fila local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.review_queue_cli --queue-json .data\review_queue.json --item 1 --status approved --reviewer Arthur --notes "ok para teste"
```

Antes da exportação final, valide o gate local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.review_queue_gate_cli --queue-json .data\review_queue.json
```

Para exportar somente as mensagens aprovadas:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.review_queue_export_cli --queue-json .data\review_queue.json --save-approved-messages-json .data\approved_messages.json --save-approved-messages-text .data\approved_messages.txt
```

A exportação final também aplica o gate automaticamente: ela bloqueia se ainda houver item pendente ou se não existir nenhuma mensagem aprovada.

Para gerar um manifesto local de publicação futura a partir das mensagens aprovadas:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.publication_manifest_cli --approved-messages-json .data\approved_messages.json --target grupo-maquiagem --save-publication-manifest-json .data\publication_manifest.json
```

Para validar o manifesto local antes de qualquer etapa futura de publicação:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.publication_manifest_validate_cli --publication-manifest-json .data\publication_manifest.json
```

O manifesto apenas registra itens `ready`, alvo planejado e data de criação. Esses comandos apenas alteram, consultam ou exportam arquivos locais. Nenhum envio é executado.

Para consolidar a revisão local em um único relatório auditável:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_review_bundle_cli --queue-json .data\review_queue.json --approved-messages-json .data\approved_messages.json --manifest-json .data\publication_manifest.json --save-bundle-json .data\local_review_bundle.json
```

O relatório consolidado registra hashes, tamanhos, contagens, checks e problemas encontrados nos arquivos locais.

Exemplos com Shopee ou Amazon sem credenciais devem retornar erro amigável, sem chamada externa real:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --niche maquiagem --marketplace shopee --dry-run
.\.venv\Scripts\python.exe -m ofertas_bot.harness --niche casa --marketplace amazon --dry-run
```

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
4. Fixtures anonimizadas com payloads reais.
5. Assinatura real da Amazon PA API.
6. Configuração controlada para HTTP real.
7. Persistência de ofertas e histórico.
8. Fila de aprovação humana.
9. Publicação controlada em canal permitido e auditável.

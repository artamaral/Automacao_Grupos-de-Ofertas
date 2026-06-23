# CI do projeto

O projeto usa GitHub Actions para validar automaticamente o código em `push`, `pull_request` e execução manual (`workflow_dispatch`).

## Workflow

Arquivo principal:

```text
.github/workflows/ci.yml
```

Etapas executadas:

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
```

## Objetivo

O CI é uma trava de qualidade para:

- manter lint e importação organizados;
- executar a suíte de testes;
- impedir regressões no pipeline dry-run;
- validar mudanças antes de qualquer etapa operacional futura.

## Regras de segurança

O CI não deve exigir segredos para passar.

Não adicionar ao CI:

- tokens;
- cookies;
- QR codes;
- sessões;
- credenciais Shopee, Amazon ou WhatsApp;
- chamadas externas reais obrigatórias.

As validações reais com `.env`, credenciais e ambiente local continuam fora do CI e devem ser feitas manualmente pelo responsável do projeto.

## Validação local equivalente

No Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

No Linux/macOS:

```bash
python -m ruff check .
python -m pytest
```

# Automação de Grupos de Ofertas

Projeto em **Python** para curadoria, pontuação e publicação controlada de ofertas de afiliados para grupos opt-in.

A primeira versão usa um **harness dry-run**: busca ofertas mockadas, pontua, gera copy, valida compliance e simula a publicação sem enviar nada para WhatsApp real.

## Princípios

- Somente grupos com entrada voluntária e consentimento claro.
- Publicação real desabilitada por padrão.
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
pip install -e .[dev]
```

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Rodar o harness

```bash
python -m ofertas_bot.harness --niche maquiagem --marketplace shopee --dry-run
```

Exemplo com Amazon mockada:

```bash
python -m ofertas_bot.harness --niche casa --marketplace amazon --dry-run
```

## Testes

```bash
pytest
```

## Estrutura

```text
src/ofertas_bot/
  agents/        # agentes funcionais do pipeline
  providers/     # integrações Shopee, Amazon, WhatsApp etc.
  harness.py     # CLI de simulação
  models.py      # modelos de domínio
  settings.py    # configuração via ambiente
  utils/         # utilidades compartilhadas
tests/
```

## Roadmap

1. Base Python dry-run com mocks.
2. Provider Shopee real.
3. Provider Amazon PA API real.
4. Persistência de ofertas e histórico.
5. Fila de aprovação humana.
6. Publicação controlada em canal permitido e auditável.

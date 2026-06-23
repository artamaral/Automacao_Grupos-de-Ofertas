# Fluxo de desenvolvimento assistido

Este projeto adota execução incremental e segura.

## Continuidade das etapas

Quando uma etapa não exigir decisão humana, credenciais, aprovação externa ou mudança de trava de segurança, a próxima etapa pode ser iniciada sem pausa desnecessária.

## Testes agrupados

Quando várias etapas independentes puderem ser validadas pelo mesmo ciclo, os testes podem ser executados uma única vez ao final do bloco.

Validação padrão:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

Se lint ou teste falhar, a correção vem antes de novas funcionalidades.

## Pontos que exigem decisão explícita

- credenciais;
- chamadas externas reais;
- publicação real;
- alteração de travas de segurança;
- aprovação humana ou de conta/app.

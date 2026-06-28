# Visao geral

## Objetivo do projeto

Construir uma operacao propria, auditavel e automatizavel para:

- receber catalogos curados;
- pontuar ofertas;
- selecionar os melhores itens;
- gerar mensagens por template;
- preparar o disparo controlado por canal;
- operar isso de forma autonoma com `n8n`.

## Pipeline principal

```text
Catalogo curado -> Collector -> Scorer -> Selecao -> Copy -> Compliance -> Dispatch
```

## Regra operacional atual

- os tres perfis operacionais principais devem avancar juntos:
  - `feminino`
  - `mae-e-bebe`
  - `auto-e-moto`
- a diferenca entre perfis deve estar em regra e dados, nao em desvio de
  implementacao;
- o fluxo default nao depende de revisao humana obrigatoria;
- o `n8n` e o ambiente alvo da operacao.

## Leitura correta da fase

- o repositorio continua sendo a fonte de codigo;
- o `n8n cloud` passa a ser o alvo da execucao;
- Google Planilhas passam a ser a superficie de manutencao das regras.

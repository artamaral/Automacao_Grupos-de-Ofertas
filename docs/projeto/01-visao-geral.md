# Visao geral

## Objetivo do projeto

Construir uma operacao propria, auditavel e automatizavel para:

- receber catalogos curados;
- pontuar ofertas;
- selecionar os melhores itens;
- gerar mensagens por template;
- preparar o disparo controlado por canal;
- operar ranking, mensagens e disparo com Supabase e Cloud Run.

## Pipeline principal

```text
Descoberta local -> Catalogo curado -> Supabase -> Ranking -> Copy -> Compliance -> Dispatch no Cloud Run
```

## Regra operacional atual

- os tres perfis operacionais principais devem avancar juntos:
  - `feminino`
  - `mae-e-bebe`
  - `auto-e-moto`
- a diferenca entre perfis deve estar em regra e dados, nao em desvio de
  implementacao;
- a descoberta e a curadoria permanecem locais;
- o fluxo em nuvem comeca no catalogo curado publicado no Supabase;
- publicacao real depende de aprovacao humana;
- Supabase e Cloud Run formam o ambiente alvo da operacao.

## Leitura correta da fase

- o repositorio continua sendo a fonte de codigo;
- os catalogos locais validados continuam sendo a origem da publicacao;
- o Supabase passa a ser a fonte de verdade operacional em nuvem;
- o Cloud Run executa geracao e disparo, sem executar descoberta;
- o `n8n` permanece apenas como legado de transicao.

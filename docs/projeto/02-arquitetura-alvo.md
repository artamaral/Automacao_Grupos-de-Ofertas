# Arquitetura alvo

## Decisao principal

O destino oficial do projeto passa a ser `n8n cloud` com operacao nativa.

Isso significa:

- nada critico deve depender do computador local ligado;
- nada critico deve depender de `self-hosted` como modelo definitivo;
- regras, estado e artefatos devem ser legiveis pela automacao;
- a manutencao operacional deve ser simples para o operador.

## Separacao de responsabilidades

### Repositorio

- codigo Python
- testes
- contratos
- documentacao
- fallback de transicao

### Google Planilhas

- descoberta
- selecao
- grupos
- cupons
- templates

### n8n

- orquestracao
- execucao operacional
- leitura de regras
- leitura de catalogos ativos
- consolidacao dos artefatos da rodada
- disparo controlado por canal

## Camadas transitorias

Ainda existem, mas nao sao o destino final:

- `self-hosted/local`
- `cloud runner` HTTP
- arquivos locais em `config/`

Essas camadas continuam uteis apenas como apoio de transicao, validacao e
fallback tecnico.

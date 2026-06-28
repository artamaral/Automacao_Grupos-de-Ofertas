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

## Camadas legadas

Ainda existem no repositorio, mas nao fazem parte do fluxo oficial:

- `self-hosted/local`
- `cloud runner` HTTP
- arquivos locais em `config/`

Regra de leitura:

- nao usar essas camadas para desenhar o workflow principal do `n8n`;
- nao referenciar `C:\...`, `app_dir`, `root_dir` ou URL de runner no contrato
  operacional oficial;
- manter essas trilhas apenas como legado tecnico e apoio de debug enquanto a
  migracao total nao estiver concluida.

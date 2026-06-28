# Cloud Runner n8n

## Status atual

O `cloud runner` deixa de ser a referencia principal do projeto.

Leitura correta:

- o fluxo oficial e `n8n-native`;
- regras e catalogos devem estar acessiveis via Google Sheets e Google Drive;
- o workflow principal nao deve depender de `runner_base_url`, `root_dir`,
  `app_dir` nem de qualquer path do computador do operador.

## Papel remanescente

O `cloud runner` pode continuar existindo apenas como:

- apoio tecnico de transicao;
- trilha de debug;
- material legado para comparar contratos antigos.

## O que nao fazer

Nao usar este documento para montar o workflow principal do `n8n`.

Se o objetivo for operacao oficial:

- siga o skeleton `n8n-native`;
- mantenha os dados operacionais no ecossistema do `n8n` e Google;
- ignore qualquer exemplo que dependa de PC local ligado.

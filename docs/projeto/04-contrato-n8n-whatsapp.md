# Contrato n8n e WhatsApp

## Canal real inicial

O primeiro canal real alvo continua sendo `WhatsApp`.

## Papel do n8n

O `n8n` deve:

- iniciar a rodada;
- ler as regras operacionais;
- acionar o pipeline;
- receber os artefatos finais;
- executar o disparo controlado;
- registrar status da rodada.

O `n8n` nao deve:

- inventar score;
- inventar copy;
- alterar banda por subnicho sem regra;
- editar manifesto manualmente.

## Precondicao de catalogo

Antes da rodada, o `n8n` deve garantir que o catalogo ativo de cada `profile`
esta disponivel dentro do proprio ecossistema operacional do workflow.

Leitura oficial:

1. o `n8n` le o registry de catalogos na superficie oficial de dados;
2. o `n8n` baixa os CSVs ativos do Google Drive;
3. o `n8n` persiste esses catálogos na sua superficie operacional;
4. a rodada segue sem depender de path local do operador.

## Artefato final esperado

O contrato final da rodada continua sendo:

- `dispatch_artifact.json`

Esse artefato deve seguir agrupado por destino e pronto para consumo do bloco
de disparo.

## Regra de seguranca

- o publisher Python continua em `dry-run` enquanto o disparo real e tratado no
  ecossistema do `n8n`;
- o envio real deve acontecer em modo controlado;
- a expansao para mais grupos depende de validacao operacional.

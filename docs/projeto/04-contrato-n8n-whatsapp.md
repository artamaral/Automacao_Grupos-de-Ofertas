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

Antes do `prepare-window`, o `n8n cloud` deve garantir que o catalogo ativo de
cada `profile` foi sincronizado.

Contrato recomendado:

1. chamar `POST /catalog-sync-plan`;
2. baixar cada CSV pelo `drive_file_id`;
3. gravar o arquivo em `target_catalog_path`;
4. seguir para `POST /prepare-window`.

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

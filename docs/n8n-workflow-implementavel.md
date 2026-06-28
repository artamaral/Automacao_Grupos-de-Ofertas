# Workflow n8n implementavel

## Leitura oficial

O workflow oficial do projeto passa a ser o `n8n-native`.

Isso significa:

- nada de `runner_base_url`;
- nada de `root_dir`;
- nada de `app_dir`;
- nada de referencia a `C:\...`;
- nada que dependa de PC local ligado.

## Arquivo oficial

- [`n8n/workflows/ofertas-rodada-skeleton.json`](../n8n/workflows/ofertas-rodada-skeleton.json)

## Sequencia oficial

1. `Trigger Rodada`
2. `Set Contexto Base`
3. `Validar Contexto`
4. `Ler Regras Google Sheets`
5. `Ler Catalog Registry`
6. `Sync Catalogos Google Drive`
7. `Selecionar Ofertas`
8. `Gerar Copy`
9. `Montar Dispatch`
10. `Persistir Log da Rodada`
11. `Notificar Conclusao`

## Dependencias aceitas

Apenas dependencias acessiveis ao `n8n`:

- Google Sheets
- Google Drive
- armazenamento do proprio ecossistema do `n8n`
- canal real configurado no `n8n`

## Dependencias proibidas no fluxo oficial

- paths locais do operador
- runner HTTP
- tunnel
- PowerShell
- filesystem local do repo como pre-requisito operacional

## Estado atual do skeleton

O skeleton oficial ja foi limpo para refletir essa decisao.

Os nos de regras, catalogo, selecao, copy e dispatch ainda estao como
placeholders tecnicos porque a implementacao nativa no `n8n` sera feita em cima
dos conectores Google e da superficie de armazenamento da propria automacao.

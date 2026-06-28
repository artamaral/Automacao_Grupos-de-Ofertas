# Proximas etapas

## Prioridade imediata

Implementar a trilha `n8n-native` sem dependencia de runner, path local ou PC
do operador.

## Sequencia recomendada

1. ler regras operacionais diretamente de Google Sheets
2. ler o `catalog_registry` diretamente de Google Sheets
3. baixar o CSV ativo de cada `profile` diretamente no `n8n`
4. persistir estado e artefatos da rodada em superficie acessivel ao `n8n`
5. remover do fluxo oficial qualquer referencia a path local e runner HTTP

## Resultado esperado

Ao final desse bloco:

- o Drive vira a origem canônica dos catalogos operacionais;
- o `n8n` passa a ter uma pasta espelho previsivel para consumo;
- o fluxo fica mais proximo de operar sem dependencia manual de catalogo local.

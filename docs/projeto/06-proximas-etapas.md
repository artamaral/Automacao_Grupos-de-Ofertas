# Proximas etapas

## Prioridade imediata

Automatizar o download ou espelho do CSV ativo do Google Drive usando o
`catalog_registry`.

## Sequencia recomendada

1. usar o `catalog_registry` como contrato unico de path
2. baixar ou sincronizar o CSV ativo de cada `profile`
3. preservar o nome padrao `clean_catalog_rating_4_8_plus.csv`
4. validar `prepare` usando os CSVs sincronizados
5. automatizar a janela de sync antes do `prepare_window`
6. expor um plano JSON de sync para o `n8n cloud`
7. depois automatizar a execucao do download via Google Drive

## Resultado esperado

Ao final desse bloco:

- o Drive vira a origem canônica dos catalogos operacionais;
- o `n8n` passa a ter uma pasta espelho previsivel para consumo;
- o fluxo fica mais proximo de operar sem dependencia manual de catalogo local.

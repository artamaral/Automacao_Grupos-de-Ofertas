# Proximas etapas

## Prioridade imediata

Implementar a sincronizacao dos catalogos CSV a partir do Google Drive.

## Sequencia recomendada

1. definir o espelho local de catalogos consumido pelo runner
2. baixar ou sincronizar o CSV ativo de cada `profile`
3. preservar o nome padrao `clean_catalog_rating_4_8_plus.csv`
4. validar `prepare` usando os CSVs sincronizados
5. depois automatizar essa etapa no `n8n`

## Resultado esperado

Ao final desse bloco:

- o Drive vira a origem canônica dos catalogos operacionais;
- o `n8n` passa a ter uma pasta espelho previsivel para consumo;
- o fluxo fica mais proximo de operar sem dependencia manual de catalogo local.

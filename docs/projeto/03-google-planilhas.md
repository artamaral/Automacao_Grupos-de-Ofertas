# Google Planilhas

## Decisao

Todos os arquivos de regras operacionais devem migrar para Google Planilhas.

Motivos:

- manutencao mais simples;
- menor dependencia de arquivo local;
- melhor compatibilidade com `n8n cloud`;
- preparacao para automacao futura de ajustes.

## Arquivo criado

Pasta oficial do projeto no Google Drive:

- `Automacao_Grupos-de-Ofertas`
- <https://drive.google.com/drive/folders/1Ta1UWp88wrAp7GXnK3Hm8xO9xboO22WQ>

Regra obrigatoria:

- todos os arquivos externos usados pelo projeto devem ficar dentro dessa
  pasta;
- a planilha principal e quaisquer futuros ativos de apoio devem ser criados ou
  movidos para la.

Planilha principal:

- `Projeto Ofertas - Regras Operacionais (Google Sheets)`
- <https://docs.google.com/spreadsheets/d/16M0S-ipgQ9lOUqCtXTd1OC80I2emERCK8ByVllR06-E/edit?usp=drivesdk>

## Abas atuais

1. `discovery_profiles`
2. `selection_profiles`
3. `group_profiles`
4. `coupon_urls`
5. `message_templates`

## Contrato minimo das abas

### discovery_profiles

Define:

- perfil
- marketplace
- query
- catalogo curado
- termos de inclusao/exclusao
- metadados de descoberta

### selection_profiles

Define:

- total de itens por rodada
- limite de itens sem venda
- cooldown
- bandas por subnicho

### group_profiles

Define:

- destinos por perfil
- canal
- limites por execucao
- limites por hora
- quiet period

### coupon_urls

Define:

- URL global ou por marketplace para cupom

### message_templates

Define:

- template textual por marketplace

## Regra de manutencao

- alteracoes operacionais devem nascer nessas abas;
- `config/` vira referencia de transicao;
- o leitor do projeto deve convergir para essa planilha como fonte principal.

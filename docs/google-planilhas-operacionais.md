# Google Planilhas operacionais

Este documento define o pacote inicial de arquivos para migrar as regras
operacionais para Google Planilhas.

Ele deve ser lido junto com
[`docs/decisao-n8n-cloud-nativo.md`](decisao-n8n-cloud-nativo.md).

## Objetivo

Substituir a manutencao operacional em arquivos locais por planilhas editaveis
no ecossistema do Google, preservando o mesmo contrato de negocio do projeto.

## Pasta oficial no Google Drive

Todos os arquivos externos usados pelo projeto devem ficar dentro da pasta:

- `Automacao_Grupos-de-Ofertas`
- <https://drive.google.com/drive/folders/1Ta1UWp88wrAp7GXnK3Hm8xO9xboO22WQ>

Isso vale para:

- planilhas operacionais;
- documentos auxiliares;
- exports de apoio;
- futuros arquivos externos consumidos por automacao.

## Abas iniciais

O pacote inicial deve ser composto por cinco abas:

1. `discovery_profiles`
2. `selection_profiles`
3. `group_profiles`
4. `coupon_urls`
5. `message_templates`

## Arquivos-semente

Os arquivos prontos para importacao inicial estao em:

```text
n8n/google_sheets_seed/discovery_profiles.csv
n8n/google_sheets_seed/selection_profiles.csv
n8n/google_sheets_seed/group_profiles.csv
n8n/google_sheets_seed/coupon_urls.csv
n8n/google_sheets_seed/message_templates.csv
```

## Regra de importacao

- cada arquivo CSV deve virar uma aba com o mesmo nome;
- a primeira linha e o cabecalho oficial;
- o conteudo inicial replica o contrato atual validado no repositorio;
- a partir da importacao, a operacao passa a tratar a planilha como fonte de
  verdade editavel.

## Ordem recomendada

1. importar `coupon_urls.csv`
2. importar `message_templates.csv`
3. importar `discovery_profiles.csv`
4. importar `selection_profiles.csv`
5. importar `group_profiles.csv`

## Observacoes de modelagem

- campos multivalorados estao serializados em `csv` dentro da celula, usando
  `|` como separador interno;
- blocos mais estruturados, como `subgroups`, estao em `json` textual;
- essa modelagem privilegia importacao simples agora e leitura automatizada em
  etapa posterior.

## Proximas etapas

1. importar as cinco abas no Google Sheets;
2. congelar o schema dessas abas;
3. criar leitor unico de planilhas no projeto;
4. fazer `n8n` consumir as planilhas em vez dos arquivos de `config/`;
5. manter `config/` apenas como referencia e fallback de transicao.

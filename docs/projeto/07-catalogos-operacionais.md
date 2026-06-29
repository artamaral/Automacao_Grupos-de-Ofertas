# Catalogos operacionais

## Decisao

Os catalogos operacionais do projeto devem ficar em `CSV`, nao em Google
Planilhas.

Separacao oficial:

- regras operacionais: Google Sheets
- catalogos operacionais: CSV no Google Drive

## Motivo

- catalogo e massa de dados grande e regeneravel;
- catalogo nao e uma superficie boa para manutencao manual em planilha;
- CSV e mais adequado para processamento, sincronizacao e reexecucao;
- o `n8n` consegue trabalhar melhor com artefato objetivo por `profile`.

## Pasta oficial no Google Drive

Todos os catalogos do projeto devem ficar dentro de:

- `Automacao_Grupos-de-Ofertas`
- `catalogs`
- `clean`

Links:

- pasta raiz do projeto:
  <https://drive.google.com/drive/folders/1Ta1UWp88wrAp7GXnK3Hm8xO9xboO22WQ>
- pasta `catalogs`:
  <https://drive.google.com/drive/folders/1jOvvZycB0Rg1rCeoB1W7rAIR3yHchig5>
- pasta `clean`:
  <https://drive.google.com/drive/folders/1D8FJRdlcvPEccWXNAO7GNqPh4Bdu0HMa>

## Estrutura atual

### feminino

- pasta:
  <https://drive.google.com/drive/folders/1M1bI46LH81Cl7EfE_nuw1l9cJcuygiBp>
- arquivo:
  <https://drive.google.com/file/d/1pym2oUMwTar27izQBt22HX2jSEhtuOzw/view?usp=drivesdk>

### mae-e-bebe

- pasta:
  <https://drive.google.com/drive/folders/1eEw9xA2jf-R8s-U8IQId9oK5Kk590O3O>
- arquivo:
  <https://drive.google.com/file/d/1WwPd048oat-JkGpbMZmiFKqhfiIcp2RV/view?usp=drivesdk>

### auto-e-moto

- pasta:
  <https://drive.google.com/drive/folders/1e6jvZWHwwj0nCLTNZSN9SO8jah73Y1b->
- arquivo:
  <https://drive.google.com/file/d/15Vh5u9OLyOBAR4qkH2PKCAjhosZ2v4iL/view?usp=drivesdk>

## Nome padrao do arquivo

Cada `profile` deve manter:

```text
clean_catalog_rating_4_8_plus.csv
```

Isso evita divergencia entre nichos e reduz condicao especial no pipeline.

## Schema operacional minimo

O arquivo ativo `clean_catalog_rating_4_8_plus.csv` deve carregar apenas o
contrato minimo consumido pelo fluxo principal.

Campos mantidos:

- `itemId`
- `productName`
- `productLink`
- `offerLink`
- `imageUrl`
- `price`
- `priceMax`
- `sales`
- `ratingStar`
- `shopType`
- `sellerCommissionRate`
- `shopeeCommissionRate`
- `subniches`

Campos fora desse bloco nao devem voltar ao CSV operacional ativo.

## Regra minima de vendas

Para o catalogo operacional ativo consumido pelo `n8n`, a regra atual e:

- manter apenas itens com `sales > 1`.

Itens com `sales = 0` ou `sales = 1` nao entram no CSV operacional ativo.

Motivo operacional atual:

- reduzir massa de linhas carregadas no `n8n cloud`;
- preservar apenas candidatos com sinal minimo de tracao;
- evitar estouro de memoria ja na etapa de leitura do CSV.

Essa regra vale para os tres `profiles` operacionais enquanto o fluxo oficial
depender do `n8n cloud` para leitura direta do catalogo.

## Contrato operacional atual

Leitura correta desta fase:

- o Google Drive passa a ser a origem canônica do catalogo ativo;
- o runner ainda consome o CSV presente no ambiente de trabalho do `n8n`;
- portanto, ainda existe uma etapa de baixar, sincronizar ou espelhar o CSV do
  Drive para a pasta operacional que o fluxo le.

## Contrato esperado no ambiente do n8n

O workflow oficial deve trabalhar assim:

- Drive = origem oficial do CSV ativo;
- `n8n` = ambiente que baixa, guarda e consome esse CSV;
- operador = nao precisa expor path local nem manter maquina ligada.

## Registry de sincronizacao

O contrato entre Google Drive e pasta local do runner passa a ser descrito por:

```text
n8n/google_sheets_seed/catalog_registry.csv
```

Campos:

- `profile`
- `relative_dir`
- `file_name`
- `drive_file_id`
- `drive_url`
- `active`

Leitura pratica:

- o Drive informa qual arquivo e o ativo de cada `profile`;
- o runner continua lendo apenas a copia espelhada em `catalogs_dir`;
- o `n8n` ou um sincronizador local deve garantir que o arquivo do Drive seja
  baixado para `catalogs_dir/<relative_dir>/<file_name>`.

## Proximo passo tecnico

Implementar a sincronizacao do catalogo ativo do Google Drive para a pasta de
catalogos que o `n8n` usa em execucao.

## Contrato operacional do espelho local

O espelho local passa a seguir exatamente o `catalog_registry.csv`.

Isso significa:

- o `runner` em Python resolve o catalogo ativo pelo registry;
- os wrappers PowerShell do `n8n` resolvem o mesmo path pelo mesmo registry;
- o script `scripts/n8n/sync_catalog_to_n8n.ps1` nao precisa mais receber
  `SourceCatalogPath` quando o arquivo padrao ja estiver em
  `catalogs/clean/<relative_dir>/<file_name>`.

Fluxo esperado:

1. o catalogo oficial e atualizado no Google Drive;
2. o operador baixa ou espelha esse CSV para `catalogs/clean/...` no repo;
3. o operador roda `sync_catalog_to_n8n.ps1 -Profile <profile>`;
4. o script copia o CSV para o path operacional definido no registry;
5. `validate_catalog`, `prepare` e `prepare_window` passam a ler esse mesmo
   path sem regra hardcoded por nicho.

Para janela multi-profile, o operador pode usar:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\n8n\invoke_sync_catalog_window.ps1 -ProfilesCsv "feminino,mae-e-bebe,auto-e-moto" -RootDir <n8n-root> -AppDir C:\Automacao_Grupos-de-Ofertas -RunId 2026-06-28-janela-01
```

## Contrato para n8n cloud

Nao referenciar:

- `C:\...`
- `root_dir`
- `app_dir`
- URL de runner HTTP

Fluxo oficial:

1. o `n8n` le o registry de catalogos em Google Sheets;
2. o `n8n` baixa o CSV ativo de cada `profile` no Google Drive;
3. o `n8n` guarda esse CSV na sua superficie operacional;
4. a rodada usa apenas dados acessiveis dentro do proprio `n8n` e Google.

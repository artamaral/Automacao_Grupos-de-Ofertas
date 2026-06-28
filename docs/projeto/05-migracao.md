# Migracao

## Objetivo

Migrar do modelo baseado em arquivo local para o modelo baseado em:

- `n8n cloud`
- Google Planilhas
- artefatos operacionais auditaveis

## Etapas

### Etapa 1 - estrutura

Ja concluido:

- decisao arquitetural registrada;
- planilha operacional criada;
- abas iniciais criadas;
- seed inicial carregado.

### Etapa 2 - leitura de planilhas no projeto

Proximo bloco tecnico:

- criar um leitor unico de Google Sheets;
- mapear abas para objetos internos do projeto;
- manter fallback temporario para `config/`.

### Etapa 3 - troca do fluxo principal

- substituir leitura de `config/` pelo leitor de planilhas;
- validar `prepare` e `finalize` usando a planilha como fonte principal.

### Etapa 4 - catalogos no Google Drive

- manter o Google Drive como origem canônica dos CSVs por `profile`;
- estruturar as pastas operacionais no Drive;
- definir o espelho operacional consumido pelo runner.

### Etapa 5 - n8n nativo

- adaptar o workflow para consumir diretamente o modelo final;
- reduzir dependencias da ponte HTTP e do modo local;
- automatizar a sincronizacao entre Drive e pasta de catalogos usada na rodada.

Bloco atual em andamento:

- expor pelo runner um `catalog-sync-plan` com `drive_file_id` e `target_catalog_path`;
- usar esse plano para o `n8n cloud` baixar os CSVs com node nativo do Google
  Drive antes do `prepare-window`.

## Regra de transicao

Durante a migracao:

- nada deve quebrar o contrato atual;
- o fallback local pode existir;
- a direcao oficial continua sendo a planilha operacional.

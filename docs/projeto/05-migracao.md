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

### Etapa 4 - n8n nativo

- adaptar o workflow para consumir diretamente o modelo final;
- reduzir dependencias da ponte HTTP e do modo local.

## Regra de transicao

Durante a migracao:

- nada deve quebrar o contrato atual;
- o fallback local pode existir;
- a direcao oficial continua sendo a planilha operacional.

# Proximas etapas

## Prioridade imediata

Implementar o leitor unico de Google Sheets no projeto.

## Sequencia recomendada

1. criar cliente de leitura da planilha principal
2. buscar por nome de aba, nao por arquivo local
3. converter linhas em estruturas do projeto
4. manter fallback temporario para `config/`
5. trocar `prepare` para usar planilhas
6. trocar `finalize` para usar o mesmo contrato
7. documentar o novo ponto unico de configuracao

## Resultado esperado

Ao final desse bloco:

- a manutencao operacional passa a acontecer na planilha;
- o projeto deixa de depender de editar `toml` e `txt` para regras do dia a dia;
- o `n8n` fica mais proximo de operar de forma autonoma.

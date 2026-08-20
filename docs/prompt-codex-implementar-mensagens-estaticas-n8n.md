# Prompt para Codex — Implementar Mensagens Estáticas no n8n

Implemente a spec definida em:

`docs/spec-n8n-mensagens-estaticas.md`

## Objetivo

Adicionar ao workflow n8n existente um processo independente de mensagens estáticas, usando Google Drive para `copy.txt` e `image.jpg`, mantendo o fluxo atual intacto.

## Regra absoluta

**NÃO MODIFIQUE O FLUXO ATUAL.**

Isso significa:

- não alterar nodes existentes;
- não alterar conexões existentes;
- não alterar triggers existentes;
- não alterar loops existentes;
- não alterar montagem de mensagem existente;
- não alterar comportamento de envio existente;
- não alterar registros existentes;
- não refatorar nodes existentes para reutilização;
- não mudar configuração WAHA existente;
- não trocar nem recriar o ID do grupo existente.

O novo processo deve ficar dentro do **mesmo arquivo/workflow visual**, em uma área separada, sem conexões de entrada ou saída com o fluxo existente.

## Antes de implementar

1. Leia `AGENTS.md`.
2. Leia `docs/spec-n8n-mensagens-estaticas.md` integralmente.
3. Inspecione o workflow n8n efetivamente usado no projeto antes de editar.
4. Identifique no workflow atual, sem modificá-los:
   - a conexão/configuração WAHA existente;
   - o ID atual do grupo `💰 Ofertas Femininas 💄👗👙👠👜`;
   - o mecanismo de registro já utilizado;
   - os nodes mínimos necessários para reproduzir o envio no novo processo.
5. Não assuma IDs, nomes de credential ou estruturas de registro. Use somente o que realmente existir no workflow.

## Implementação esperada

Criar no mesmo workflow visual um processo separado com esta lógica:

```text
Schedule Trigger configurável
        ↓
resolver msg_XXX correspondente à execução do dia
        ↓
Google Drive
        ↓
localizar pasta msg_XXX
        ↓
validar copy.txt e image.jpg
        ↓
      disponível?
       /      \
     sim      não
      ↓        ↓
 carregar    reutilizar
 copy/img    registro existente
      ↓        ↓
 usar mesmo  finalizar
 grupo/ID    normalmente
      ↓
 usar mesma configuração WAHA
      ↓
 enviar WhatsApp
      ↓
 reutilizar registro existente
```

## Schedule Trigger

Use **um único `Schedule Trigger`** exclusivo do novo processo.

Ele deve aceitar múltiplas regras de horário para permitir aumentar ou reduzir a quantidade de mensagens diárias apenas alterando a configuração do trigger.

O sequenciamento esperado é:

```text
1ª execução do dia → msg_001
2ª execução do dia → msg_002
3ª execução do dia → msg_003
...
```

Não crie um trigger por mensagem.

## Google Drive

A implantação deve prever a configuração da conexão n8n ↔ Google Drive usando a conta:

`grupodeofertas.mktdigital@gmail.com`

Não versionar token, segredo, credential exportada ou qualquer dado sensível.

Estrutura esperada:

```text
msg_001/
  copy.txt
  image.jpg

msg_002/
  copy.txt
  image.jpg
```

Cada execução deve acessar somente a pasta `msg_XXX` correspondente.

Não processar todas as pastas do dia ou todas as pastas disponíveis.

## Ausência de mensagem

Se houver mais execuções configuradas que mensagens disponíveis, ou se faltar `copy.txt` ou `image.jpg`:

- não enviar mensagem ao WhatsApp;
- não provocar falha global do workflow;
- reutilizar exclusivamente o mecanismo de registro já existente;
- não criar novo status, tabela, schema, tipo de log ou estrutura de persistência;
- finalizar normalmente a execução atual.

## WAHA e grupo

Manter exatamente a configuração existente.

Grupo obrigatório:

`💰 Ofertas Femininas 💄👗👙👠👜`

Use o **mesmo ID já existente no workflow**.

Não crie nova sessão WAHA, nova conexão, novo grupo nem ID paralelo.

## Forma de alteração do workflow

O novo processo pode replicar nodes mínimos de envio/registro quando necessário.

**Não extraia, mova, renomeie, reconecte ou refatore nodes atuais.**

A implementação deve ser aditiva.

## Validação obrigatória

Antes de concluir:

1. Compare o workflow antes e depois e confirme que todos os nodes e conexões preexistentes permanecem sem alterações funcionais.
2. Confirme que o novo processo não possui conexão com o fluxo atual.
3. Confirme que existe somente um novo `Schedule Trigger` para mensagens estáticas.
4. Confirme que múltiplos horários podem ser configurados nesse trigger.
5. Confirme que cada execução resolve somente uma `msg_XXX`.
6. Confirme que ausência de pasta/copy/imagem não envia WhatsApp.
7. Confirme que o registro usado é um mecanismo já existente.
8. Confirme que o mesmo ID do grupo e a mesma configuração WAHA foram usados.
9. Valide que o JSON final é importável pelo n8n.
10. Não habilite envio real nem altere credenciais durante a edição do repositório.

## Entrega

Ao finalizar, informe objetivamente:

- arquivo(s) alterado(s);
- nodes novos criados;
- como configurar os horários diários;
- quais credenciais do Google Drive precisam ser configuradas manualmente no n8n;
- qual mecanismo existente de registro foi reutilizado;
- confirmação explícita de que o fluxo atual não foi modificado.

Se algum requisito depender de informação que não existe no repositório/workflow, **não invente**. Pare nesse ponto específico e informe exatamente o dado faltante.

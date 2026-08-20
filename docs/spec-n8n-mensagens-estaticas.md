# Spec — Mensagens Estáticas no n8n

## Objetivo

Adicionar ao **mesmo arquivo/workflow visual do n8n** um novo processo para envio de mensagens previamente preparadas.

**O FLUXO ATUAL NÃO DEVE SER MODIFICADO.**

O novo processo deve ser criado em outra área do mesmo workflow, sem alterar nodes, conexões, triggers, loops, montagem de mensagens, envio, registros ou qualquer comportamento já existente.

## Regra de isolamento

Obrigatório:

- não alterar nenhum node existente;
- não alterar nenhuma conexão existente;
- não alterar nenhum trigger existente;
- não inserir `IF`, `Merge`, `Switch` ou branches no fluxo atual;
- não refatorar o fluxo atual para atender esta funcionalidade;
- não criar novos tipos de registro ou novas estruturas de log;
- não alterar a conexão existente com WAHA;
- não alterar o grupo ou o ID de grupo já utilizado.

Se alguma funcionalidade necessária existir apenas no fluxo atual, ela deve inicialmente ser **replicada no novo processo**, e não extraída ou refatorada.

## Estrutura visual

```text
┌──────────────────────────────┐
│ FLUXO ATUAL                  │
│                              │
│ NÃO ALTERAR                  │
│ NÃO MODIFICAR                │
│ NÃO CONECTAR AO NOVO FLUXO   │
└──────────────────────────────┘

┌──────────────────────────────┐
│ NOVO PROCESSO                │
│ MENSAGENS ESTÁTICAS          │
│                              │
│ Schedule Trigger próprio     │
│ → resolver msg_XXX           │
│ → Google Drive               │
│ → carregar copy + imagem     │
│ → enviar WhatsApp            │
│ → usar registro existente    │
└──────────────────────────────┘
```

## Google Drive

A integração do n8n com o Google Drive faz parte do escopo da implantação.

Conta a ser utilizada:

`grupodeofertas.mktdigital@gmail.com`

A autenticação deve ser configurada no n8n durante a implantação e **nenhuma credencial ou segredo deve ser versionado no repositório**.

O novo processo deve conseguir:

- localizar a pasta da mensagem;
- listar os arquivos da pasta;
- carregar a copy;
- carregar a imagem;
- usar os dois arquivos no envio.

Estrutura esperada:

```text
msg_001/
  copy.txt
  image.jpg

msg_002/
  copy.txt
  image.jpg

msg_003/
  copy.txt
  image.jpg
```

A data não precisa fazer parte do nome da pasta.

Cada execução deve procurar **somente a pasta correspondente à mensagem daquela execução**. O processo não deve enviar automaticamente todas as pastas existentes no Drive.

## Trigger configurável

Criar **um único `Schedule Trigger`** exclusivo para o novo processo.

Esse node deve permitir configurar múltiplos horários diários. A quantidade de horários configurados determina a quantidade máxima de mensagens estáticas executadas no dia.

Exemplo:

```text
09:30 → msg_001
11:00 → msg_002
14:30 → msg_003
16:00 → msg_004
```

Aumentar ou diminuir a quantidade de mensagens diárias deve exigir apenas ajuste das regras de horário desse `Schedule Trigger`, sem mudar o restante do processo.

## Sequenciamento

As execuções do dia devem mapear sequencialmente para as mensagens:

```text
1ª execução → msg_001
2ª execução → msg_002
3ª execução → msg_003
4ª execução → msg_004
...
```

O processo deve resolver o `msg_id` correspondente à execução atual e então acessar somente essa pasta no Google Drive.

## Mensagem inexistente ou incompleta

Pode haver mais horários configurados no n8n do que mensagens disponíveis no Google Drive.

Exemplo:

```text
Horários configurados:
09:30 → msg_001
11:00 → msg_002
14:30 → msg_003
16:00 → msg_004

Drive disponível:
msg_001
msg_002
msg_003
```

Se `msg_004` não existir, ou se faltar `copy.txt` ou `image.jpg`, o processo deve:

```text
detectar ausência/incompletude
→ NÃO enviar WhatsApp
→ usar o mecanismo de registro já existente no workflow
→ finalizar normalmente essa execução
```

A ausência de mensagem preparada não deve derrubar o workflow.

**Nenhum novo tipo de registro deve ser criado.** Deve ser reutilizada a estrutura de registro já existente no fluxo atual, usando somente campos/status compatíveis com ela.

## WhatsApp / WAHA

A conexão atual com WhatsApp via **WAHA permanece igual**.

O novo processo deve utilizar o mesmo grupo já existente:

`💰 Ofertas Femininas 💄👗👙👠👜`

Deve ser utilizado **o mesmo ID de grupo já existente no workflow atual**.

Não criar:

- nova sessão WAHA;
- nova conexão WAHA;
- novo ID de grupo;
- duplicação de configuração de grupo.

## Processo novo

```text
Schedule Trigger configurável
        ↓
resolver msg_XXX da execução
        ↓
Google Drive
        ↓
localizar pasta msg_XXX
        ↓
validar copy.txt + image.jpg
        ↓
      disponível?
       /      \
     sim      não
      ↓        ↓
 carregar   usar registro
 copy/img   existente
      ↓        ↓
 usar mesmo finalizar
 grupo/ID
      ↓
 usar mesma conexão WAHA
      ↓
 enviar WhatsApp
      ↓
 usar registro existente
```

## Critérios de aceite

1. O processo novo está no mesmo arquivo/workflow visual do n8n.
2. Nenhum node ou conexão do fluxo atual foi modificado.
3. O novo processo possui um único `Schedule Trigger` configurável com múltiplos horários.
4. A quantidade de mensagens diárias pode ser aumentada ou reduzida ajustando apenas os horários do trigger.
5. Cada execução resolve uma única pasta `msg_XXX`.
6. Copy e imagem são carregadas do Google Drive.
7. A integração com Google Drive é configurada usando a conta `grupodeofertas.mktdigital@gmail.com` durante a implantação, sem versionar credenciais.
8. Se pasta, copy ou imagem estiverem ausentes, nenhum WhatsApp é enviado e a execução termina normalmente.
9. Nessas ocorrências é reutilizado exclusivamente o mecanismo de registro já existente.
10. O envio usa a conexão WAHA existente.
11. O envio usa o mesmo ID existente do grupo `💰 Ofertas Femininas 💄👗👙👠👜`.
12. Nenhum novo tipo de registro, sessão WAHA ou configuração paralela de grupo é criado.

## Restrição principal

**ADICIONAR SOMENTE O NOVO PROCESSO. O FLUXO ATUAL NÃO DEVE SER MODIFICADO.**

# Fan-out WAHA: clone de teste

O workflow `OfertasMvpSupab1-TestFanout` valida a mesma mensagem para um grupo
e um canal WhatsApp sem alterar o workflow real `OfertasMvpSupab1`.

## Configuracao operacional

Nas variaveis nativas da instancia n8n, configurar apenas fora do Git:

- `N8N_TEST_FANOUT_GROUP_CHAT_ID`: chat ID do grupo de teste, com sufixo `@g.us`.
- `N8N_TEST_FANOUT_CHANNEL_CHAT_ID`: chat ID do canal de teste, com sufixo
  `@newsletter`.
- `N8N_TEST_FANOUT_REAL_SEND_ENABLED=true`: habilita o envio real do clone.

O clone usa `$vars`, nao `$env`, para manter
`N8N_BLOCK_ENV_ACCESS_IN_NODE=true` e impedir que os nos Code tenham acesso
ao ambiente completo da instancia.

O JSON versionado mantem apenas os nomes logicos `grupo-teste-fanout` e
`canal-teste-fanout`. O clone permanece `active=false` apos importacao.

## Limites do clone

- Os tres fluxos usam a mesma lista `destinations[]`: recorrente Supabase,
  mensagens estaticas e mensagens pontuais.
- O recorrente usa o `Trigger Manual` original. As mensagens estaticas e
  pontuais usam, respectivamente, `Trigger Manual Estatico Fanout Teste` e
  `Trigger Manual Pontual Fanout Teste`; execute somente o gatilho do fluxo
  que esta sendo validado.
- No recorrente, o gatilho manual consulta a primeira janela pronta a partir
  da hora atual (`next_ready_today`), para nao disputar corrida com o cron de
  producao. O gatilho agendado do clone continua consultando somente a hora
  corrente (`current_slot`). Ambos sao apenas previsualizacao: nao fazem claim
  nem alteram a fila diaria.
- Cada destino passa por loop sequencial e `/api/sendImage`.
- O recorrente consulta somente uma previa e nunca claima a fila diaria.
- O clone nao grava nem atualiza `offers.publication_events`.
- O fluxo pontual nao move a pasta `msg_XXX`; a mensagem permanece em
  pendentes para permitir repeticao segura.

A execucao do n8n, a resposta do WAHA e a verificacao manual no grupo/canal
sao as evidencias da validacao. Aceite do WAHA nao substitui a observacao do
conteudo nos destinos.

## Importacao autorizada

Local Windows PowerShell, antes de qualquer VPS:

```powershell
.\.venv\Scripts\python.exe scripts\n8n\build_test_fanout_workflow.py
.\.venv\Scripts\python.exe scripts\n8n\deploy_test_fanout_workflow_guard.py
```

Na VPS Ubuntu/bash, somente depois de autorizacao explicita de deploy:

```bash
cd /opt/automacao_grupo_compras/app
python3 scripts/n8n/deploy_test_fanout_workflow_guard.py --apply
```

Primeiro importar o JSON pelo painel do n8n como inativo; o comando acima
somente atualiza esse clone ja importado e reforca `active=false`. Credenciais
WAHA e Google Drive sao revisadas e associadas no painel; ativacao e execucao
manual sao etapas separadas.

## Rollout real posterior

O ledger atual permite somente um evento por `dispatch_plan_id`. Antes de
fan-out no workflow real, criar uma migracao que permita um evento por
`(dispatch_plan_id, target)`, adicione `fanout_run_id` e
`is_dispatch_owner`, mantenha um unico destino canonicamente responsavel pelo
slot e deduplique o cooldown por `fanout_run_id`.

Depois desse rollout, a auditoria por destino sera feita em
`offers.publication_events` por `fanout_run_id` e `target`; o `payload` deve
conter `target_chat_id`, `destination_kind`, `source_flow` e a resposta WAHA.

### Checklist obrigatoria baseada na validacao do clone

O rollout para `OfertasMvpSupab1` deve replicar os seguintes pontos. Eles sao
requisitos, nao melhorias opcionais:

- manter `N8N_BLOCK_ENV_ACCESS_IN_NODE=true`; os destinos operacionais devem
  ser lidos por `$vars`, nunca por `$env`, e IDs de producao nao podem entrar
  no JSON versionado;
- configurar `destinations[]` uma vez por execucao e restaurar essa
  configuracao nos expansores. Os nos de Google Drive e Supabase podem
  substituir o item de entrada e remover campos do contexto;
- executar cada `Expandir Destinos` em `runOnceForAllItems`. O expansor retorna
  um item por destino, portanto nao pode usar `runOnceForEachItem`;
- preservar o loop sequencial e o pacing para cada destino nos tres fluxos;
- preparar `/api/sendImage` com `image_url -> waha_image_url` e filename. O
  workflow nao deve exigir `waha_image_base64`, pois esse campo nao faz parte
  do contrato dos fluxos atuais;
- no preparador WAHA de producao, aceitar explicitamente `@newsletter` alem
  de `@g.us` e chats individuais. A validacao de `destination_kind` deve
  impedir sufixos trocados antes do envio;
- registrar resultado por destino, inclusive falhas, com `fanout_run_id`,
  `target`, `target_chat_id`, `destination_kind`, `source_flow`, resposta WAHA
  e identificador da mensagem;
- deixar somente o destino canonico como `is_dispatch_owner=true`. Apenas ele
  pode consumir o slot da fila e projetar cooldown; os demais eventos permanecem
  auditaveis, mas nao duplicam esses efeitos;
- manter a consulta recorrente de producao estrita na hora corrente e com o
  claim controlado. O modo manual `next_ready_today` foi criado apenas para o
  clone e nao pertence ao workflow real;
- aplicar workflow e migracao como inativos, revisar credenciais e destinos no
  painel e autorizar ativacao separadamente;
- apos qualquer validacao real do clone, voltar
  `N8N_TEST_FANOUT_REAL_SEND_ENABLED` para `false`.

O aceite do rollout exige evidencia em tres superficies: resposta normalizada
do WAHA, observacao dos destinos e eventos por destino no Supabase. Sucesso da
execucao n8n, isoladamente, nao comprova entrega.

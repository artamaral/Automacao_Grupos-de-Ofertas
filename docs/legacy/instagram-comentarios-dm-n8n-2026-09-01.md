# Legado: comentarios e DMs Instagram via n8n

Data de encerramento: 2026-09-01

## Decisao

O fluxo proprio de comentarios e DMs do Instagram foi descontinuado. A
operacao passa a usar a automacao nativa configurada no Meta Business Suite
para palavras-chave, resposta publica e mensagem direta.

Esta decisao nao altera os workflows de publicacao diaria do Instagram,
WhatsApp, planner, ranking ou tracking.

## Motivo

O endpoint e o workflow foram construidos e testados como infraestrutura, mas
o app proprio nao recebeu os eventos reais de comentarios de contas externas
no modelo de autorizacao disponivel. A automacao nativa da Meta foi configurada
manualmente e se torna o caminho operacional. Nao manter o fluxo proprio evita
operar um webhook e credenciais sem uso.

## Historico resumido

1. Foi criada a especificacao isolada para comentarios, respostas publicas e
   DMs, sem alterar a publicacao diaria.
2. Foram criados no Google Drive os arquivos editoriais de introducao, resposta
   publica, DM padrao e palavras-chave.
3. A migracao `202608310002_instagram_interactions.sql` criou os ledgers
   `offers.instagram_comment_events` e `offers.instagram_dm_events`.
4. Foi criado o workflow n8n `OfertasInstagramInteractionsSupab1`, com o
   verificador HTTP `n8n/instagram_webhook_verifier.py` para o challenge da
   Meta e processamento de eventos.
5. O workflow recebeu correcoes de roteamento e de endpoint para Facebook
   Login. Esses ajustes corrigiram a infraestrutura, mas nao constituem prova
   de recebimento ou entrega para contas externas.
6. Apos os testes reais sem gatilho para comentarios externos, foi adotada a
   automacao manual nativa da Meta.
7. Em 2026-09-01, o workflow foi despublicado, o verificador dedicado foi
   parado e o n8n foi reiniciado para aplicar o estado desativado.

## Estado final confirmado

- Workflow `OfertasInstagramInteractionsSupab1`: despublicado.
- Versao ativa do workflow: ausente.
- Servico `instagram-webhook-verifier`: parado.
- Endpoint de callback proprio: inativo porque dependia desse servico.
- Credenciais n8n, arquivos editoriais no Drive, codigo e testes: preservados
  apenas para historico; nao devem ser usados por fluxo ativo.

## Artefatos preservados como legado

- `docs/spec-instagram-comentarios-dm-n8n.md`
- `n8n/workflows/ofertas-instagram-interactions-supabase.json`
- `scripts/n8n/deploy_instagram_interactions_workflow_guard.py`
- `n8n/instagram_webhook_verifier.py`
- `supabase/migrations/202608310002_instagram_interactions.sql`
- `tests/test_instagram_interactions_migration.py`
- `tests/test_n8n_instagram_interactions_workflow_guard.py`
- `tests/test_instagram_webhook_verifier.py`

Nenhum segredo, token de acesso, token de verificacao, URL de convite ou valor
de credencial e registrado neste documento.

## Substituto operacional

A automacao nativa deve manter uma regra por intencao, por exemplo `QUERO` e
`MAIS INFO`, com resposta publica e DM configuradas no Meta Business Suite.
Para a resposta de DM aprovada, a primeira linha usa a rota controlada do grupo:

`https://mktdigitalofertas.com.br/go/whatsapp/feminino`

Depois dela, usar texto breve e o site:

`https://mktdigitalofertas.com.br/feminino`

## Avaliacao das tabelas Supabase

Auditoria remota em 2026-09-01:

- `offers.instagram_comment_events`: existe, 0 linhas, 73728 bytes;
- `offers.instagram_dm_events`: existe, 0 linhas, 57344 bytes;
- nao ha views ou outras relacoes dependentes dessas tabelas;
- ha somente uma chave estrangeira opcional de
  `instagram_comment_events.publication_event_id` para
  `offers.publication_events.publish_id`, com `ON DELETE SET NULL`;
- a migracao foi registrada como aplicada.

Conclusao: a remocao e tecnicamente simples e de baixo risco para o estado
atual, pois os dois ledgers estao vazios e nao possuem consumidores
operacionais. Mesmo assim, nenhuma tabela foi removida nesta decisao: manter o
registro por enquanto permite auditoria e retorno controlado durante a
validacao da automacao nativa.

Caso a remocao seja aprovada depois da validacao da operacao nativa, criar uma
nova migracao destrutiva separada que remova primeiro as tabelas e seus objetos
dependentes. Nunca editar, apagar ou reexecutar a migracao historica ja
aplicada `202608310002_instagram_interactions.sql`.

## Regra para qualquer reativacao futura

Uma reativacao exige nova decisao explicita, autorizacao de producao adequada
na Meta, credenciais dedicadas, revisao de seguranca, nova publicacao do
workflow e teste real de recebimento e entrega. O codigo legado nao deve ser
reativado por acidente.

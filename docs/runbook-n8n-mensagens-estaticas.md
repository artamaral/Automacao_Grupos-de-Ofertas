# Runbook n8n - Mensagens Estaticas

Este documento descreve a configuracao, o teste e a operacao do processo de
mensagens estaticas adicionado ao workflow `OfertasMvpSupab1`.

## Escopo e arquitetura

O processo fica no mesmo workflow visual do fluxo de ofertas, mas e isolado:

- os 18 nodes legados e suas conexoes permanecem congelados pelo guard;
- o bloco estatico possui 21 nodes e conexoes somente entre eles;
- existe um unico `Schedule Mensagens Estaticas` para o novo processo;
- o workflow versionado permanece `active=false`;
- credenciais, tokens e segredos do Google nao sao versionados.

O fluxo operacional e:

```text
Schedule Mensagens Estaticas
  -> resolver msg_XXX da execucao do dia
  -> localizar ofertas-femininas/msg_XXX no Google Drive
  -> validar copy.txt e image.jpg
  -> baixar os dois arquivos
  -> preparar texto e imagem em base64
  -> validar allowlist
  -> enviar imagem pelo WAHA
  -> registrar em offers.publication_events
```

Qualquer ausencia, duplicidade ou arquivo invalido encerra somente a execucao
atual como `cancelled`, sem chamar o WAHA e sem causar falha global.

## Horarios e sequenciamento

O Schedule Trigger possui duas regras no timezone `America/Sao_Paulo`:

| Ordem | Horario | Cron |
| --- | --- | --- |
| 1 | 09:30 | `30 9 * * *` |
| 2 | 17:30 | `30 17 * * *` |

O node `Resolver Sequencia Estatica` usa
`$getWorkflowStaticData('node')`. A primeira execucao publicada de cada dia
resolve `msg_001`, a segunda `msg_002` e assim por diante. O contador reinicia
quando muda a data operacional.

Para aumentar ou reduzir a quantidade diaria, altere somente as regras do
Schedule Trigger. Nao crie um trigger por mensagem.

Dados estaticos do workflow persistem apenas em execucoes de um workflow
publicado e iniciadas por trigger. Uma execucao manual serve para validar o
caminho, mas nao representa o sequenciamento persistente de producao.

## Estrutura no Google Drive

A conta operacional e:

```text
grupodeofertas.mktdigital@gmail.com
```

A estrutura deve usar nomes exatos:

```text
ofertas-femininas/
  msg_001/
    copy.txt
    image.jpg
  msg_002/
    copy.txt
    image.jpg
```

Regras:

- deve existir exatamente uma pasta raiz `ofertas-femininas`;
- deve existir exatamente uma pasta para o `msg_XXX` corrente;
- cada pasta deve conter exatamente um `copy.txt` e um `image.jpg`;
- `copy.txt` deve conter texto UTF-8 nao vazio;
- `image.jpg` deve ser uma imagem JPEG nao vazia;
- cada execucao consulta somente o `msg_XXX` correspondente.

Duplicidade de pasta ou arquivo e tratada como indisponibilidade para impedir
que o workflow escolha um conteudo ambiguo.

## OAuth2 do Google Drive

No Google Cloud Console:

1. Crie ou selecione o projeto da automacao.
2. Ative a `Google Drive API`.
3. Configure a tela de consentimento OAuth como `External`.
4. Enquanto o aplicativo estiver em teste, adicione
   `grupodeofertas.mktdigital@gmail.com` em `Test users`.
5. Crie um OAuth Client ID do tipo `Web application`.
6. Cadastre exatamente esta URI de redirecionamento:

```text
https://n8n-owco.srv1805131.hstgr.cloud/rest/oauth2-credential/callback
```

Uma `Authorized JavaScript origin`, quando exigida, deve conter somente a
origem, sem caminho e sem barra final:

```text
https://n8n-owco.srv1805131.hstgr.cloud
```

No n8n, crie uma credencial `Google Drive OAuth2 API`, informe o Client ID e o
Client Secret e conclua `Sign in with Google`. Associe a mesma credencial aos
cinco nodes Google Drive do bloco estatico.

O JSON do repositorio omite propositalmente o ID dessa credencial. Depois de
uma importacao ou reaplicacao do JSON versionado, confirme a associacao dos
cinco nodes antes de publicar o workflow. Aplicativos Google mantidos em modo
`Testing` tambem podem exigir nova autorizacao periodica.

### Erro 403 access_denied

Se o Google informar que o aplicativo esta em testes e permite apenas
testadores aprovados:

1. abra `Google Auth Platform > Audience` no projeto correto;
2. mantenha o tipo de usuario como `External`;
3. adicione a conta operacional em `Test users`;
4. salve e repita a conexao no n8n com essa mesma conta.

## WAHA e grupo

O destino oficial versionado permanece:

```text
target: grupo-ofertas-feminino
chatId: 120363412864266334@g.us
session: default
endpoint: http://waha:3000/api/sendImage
credential: WAHA Header Auth
```

O envio usa `file.data` em base64. O destino precisa passar pela allowlist antes
do request HTTP.

Para descobrir o ID de um grupo de teste, a conta conectada na sessao WAHA
`default` deve participar dele. Execute temporariamente um HTTP Request com:

```text
GET http://waha:3000/api/default/groups
```

Parametros recomendados:

```text
limit=100
offset=0
sortBy=subject
sortOrder=asc
exclude=participants
```

Use a credencial `WAHA Header Auth`. Se o grupo acabou de ser criado, atualize
a sessao ou repita a consulta. O campo `_serialized`, terminado em `@g.us`, e o
ID usado no envio.

## Teste controlado

O workflow legado ja possui um Manual Trigger. O n8n permite apenas um node
desse tipo por workflow, portanto nao adicione outro. Para validar o bloco
estatico sem aguardar o horario oficial:

1. crie `ofertas-femininas/msg_001` no Drive;
2. envie um `copy.txt` UTF-8 e um `image.jpg` JPEG validos;
3. associe a credencial Drive aos cinco nodes;
4. altere temporariamente o destino e a allowlist somente nos nodes novos;
5. adicione temporariamente uma regra proxima ao Schedule Trigger, ou execute o
   proprio trigger pelo editor quando essa opcao estiver disponivel;
6. publique e acompanhe uma unica execucao;
7. confirme o recebimento no grupo de teste e o registro em
   `offers.publication_events`;
8. restaure o grupo oficial, remova a regra temporaria e publique novamente.

Grupo usado na validacao de 2026-08-20:

```text
subject: Grupo messagem - teste
chatId: 120363430277405319@g.us
```

Nao habilite uma segunda sessao WAHA e nao altere os nodes do fluxo legado.

## Diagnostico de cancelamento

Quando um IF seguir pela saida `false`, abra o output do node anterior e
verifique `blocked_reason` ou os contadores retornados.

Motivos esperados incluem:

- `root_folder_missing_or_ambiguous`;
- `message_folder_missing_or_ambiguous`;
- `copy_missing_or_invalid`;
- `image_missing_or_invalid`;
- arquivo vazio ou MIME type incompativel;
- destino fora da allowlist.

Na imagem em que `IF Pasta msg_XXX Disponivel` seguiu por `false`, a pasta
correspondente ao `msg_XXX` daquela execucao nao foi encontrada de forma unica.
Isso pode ocorrer quando o teste criou `msg_001`, mas o contador persistente ja
resolveu outro numero. Confirme o `msg_id` no output de
`Resolver Sequencia Estatica` e o parent ID usado na busca.

## Evidencia do teste de 2026-08-20

A validacao progrediu em quatro execucoes:

| Execucao | Resultado |
| --- | --- |
| 252 | `message_folder_missing`, finalizada como `cancelled` |
| 253 | copy localizada, `image_missing_or_invalid`, `cancelled` |
| 254 | envio manual confirmado como imagem |
| 255 | disparo por trigger confirmado como imagem |

A execucao 255 iniciou em `2026-08-20T19:00:00.055Z` e registrou:

```text
adapter_status=sent_to_adapter
adapter_response_type=image
delivery_status=confirmed
sent_at=2026-08-20T19:00:08.571Z
publish_id=3102b6a2-a499-4e67-aa87-e10d4e599fac
```

O recebimento no grupo de teste foi confirmado pelo operador. Apos o teste, o
workflow publicado foi restaurado para o grupo oficial.

Estado remoto conferido apos a restauracao:

```text
active=true
versionCounter=88
versionId=9eb844cd-ee6e-4d91-89ad-48a48be4b77b
39 nodes funcionais + 2 sticky notes
4 regras de horario oficiais
5 nodes Drive com credencial associada
destino de producao presente e destino de teste ausente
n8n 2.32.6 healthy
```

As duas sticky notes existentes no editor foram preservadas.

## Validacao local

Execute no Windows PowerShell, na raiz do repositorio:

```powershell
.\.venv\Scripts\python.exe -m ruff check scripts\n8n\deploy_workflow_guard.py tests\test_n8n_deploy_workflow_guard.py
.\.venv\Scripts\python.exe -m pytest tests\test_n8n_deploy_workflow_guard.py -q
.\.venv\Scripts\python.exe scripts\n8n\deploy_workflow_guard.py --dry-run --preserve-pindata
```

O guard deve confirmar:

- hashes canonicos dos 18 nodes e conexoes legados;
- ausencia de conexao cruzada entre os dois blocos;
- exatamente um Schedule Trigger novo;
- quatro regras oficiais;
- destino, sessao e endpoint WAHA oficiais;
- ausencia de credenciais Google e segredos no JSON;
- todos os caminhos de indisponibilidade chegando a `cancelled` sem WAHA.

## Deploy e sincronizacao do repositorio

O checkout Git e o workflow armazenado pelo n8n sao estados distintos.
Executar `git pull` no VPS atualiza codigo e documentacao, mas nao importa nem
publica automaticamente o JSON no banco do n8n.

Antes de qualquer reaplicacao do workflow:

1. confirme que o checkout remoto esta limpo;
2. execute o guard em dry-run;
3. mantenha o workflow importado inativo durante a verificacao;
4. reassocie manualmente as cinco credenciais Drive;
5. confira horarios, grupo oficial e allowlist;
6. publique somente depois dessas verificacoes.

Uma reaplicacao deve preservar `pinData` quando solicitado e nunca deve
versionar credenciais. A prova de entrega exige o evento `confirmed` em
`offers.publication_events`; sucesso da execucao do n8n ou aceitacao do adapter,
isoladamente, nao bastam.

## Checklist de encerramento

- grupo oficial restaurado;
- regra temporaria removida;
- horarios oficiais presentes;
- cinco credenciais Drive associadas;
- workflow ativo e saudavel;
- registro `confirmed` conferido;
- JSON local continua `active=false` e sem segredos;
- checkout do VPS sincronizado sem importar o workflow novamente.

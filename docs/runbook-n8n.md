# Runbook n8n MVP

Este runbook descreve apenas o fluxo MVP.

Fluxos antigos com runner HTTP, self-hosted/local, Cloud Run ou Google
Planilhas como fonte principal ficam como referencia historica. Eles nao devem
guiar a primeira operacao minima.

## Fluxo oficial

```text
Trigger
  -> Definir contexto
  -> Consultar Supabase
  -> Montar mensagens
  -> Validar allowlist
  -> Enviar ou simular envio
  -> Registrar resultado no Supabase
```

## Entradas minimas

O workflow deve receber ou definir:

- `profile`: exemplo `feminino`;
- `marketplace`: exemplo `shopee`;
- `limit`: quantidade maxima de ofertas da rodada;
- `target`: destino logico do envio;
- `dry_run`: `true` por padrao;
- `run_id`: identificador da rodada.

## Credenciais

Configurar no n8n, fora do Git:

- conexao segura com Supabase;
- credencial do canal de envio;
- allowlist de destinos permitidos;
- template ou texto-base da mensagem.

## Adapter WhatsApp atual

O adapter WhatsApp definido para uso agora e o WAHA self-hosted.

A decisao completa esta em
[`docs/decisao-waha-whatsapp-n8n.md`](decisao-waha-whatsapp-n8n.md).

Leitura operacional:

- usar WAHA apenas como canal de envio, nao como fonte de verdade;
- manter `dry_run=true` por padrao;
- validar allowlist antes de chamar o adapter;
- registrar aceite, falha, bloqueio ou sessao desconectada em
  `offers.publication_events`;
- nao versionar API key, QR Code, sessoes, cookies, tokens ou `.env`;
- nao tratar aceite do adapter como prova absoluta de entrega final.

## Acessos para iniciar

Antes de criar arquivos na VPS ou executar o fluxo real, separar os acessos por
responsabilidade.

## Hospedagem proposta: Hostinger VPS

Para o MVP, a proposta e rodar o n8n self-hosted em uma VPS da Hostinger.

Objetivo:

- manter o n8n em ambiente sempre disponivel;
- evitar dependencia do PC local ligado;
- permitir manutencao pelo VSCode Remote SSH;
- manter segredos fora do repositorio;
- importar o workflow versionado do projeto no painel do n8n.

Leitura operacional:

- a VPS hospeda o n8n e seus dados persistentes;
- o repositorio continua sendo a fonte de workflows exportaveis, payloads de
  exemplo, docs e scripts de apoio;
- credenciais reais ficam no painel do n8n, no banco/volume persistente do n8n
  ou em arquivos locais da VPS excluidos do Git;
- a conexao com Supabase deve usar credencial especifica para a operacao do
  workflow, nunca secrets versionados;
- acesso SSH deve usar chave local, nao senha colocada em documento.

### Implantacao atual da VPS

Estado implantado em 2026-08-08:

- diretorio operacional: `/opt/automacao_grupo_compras/n8n`;
- Compose com `n8n` 2.32.6, `n8nio/runners` 2.32.6 e Postgres
  16.14 Alpine;
- dados persistentes em `data/n8n` e `data/postgres`;
- `.env` local com modo `0600`, fora do repositorio;
- URL publica de webhooks configurada via `N8N_WEBHOOK_URL`;
- timezone `America/Sao_Paulo` em `TZ` e `GENERIC_TIMEZONE`;
- painel em `https://n8n-owco.srv1805131.hstgr.cloud/`, servido pelo
  Traefik existente;
- porta `5678` publicada somente em `127.0.0.1`; Postgres sem porta publicada;
- workflow `ofertas-mvp-supabase` importado e inativo;
- credencial Postgres para o Supabase criada no painel do n8n;
- primeiro `dry_run` manual executado com sucesso em 2026-08-09.

O Postgres local guarda somente o estado interno do n8n. O Supabase continua
como fonte de verdade para catalogo, ranking e historico de publicacao.

Comandos operacionais:

```bash
cd /opt/automacao_grupo_compras/n8n
docker compose --env-file .env -f docker-compose.yml ps
docker compose --env-file .env -f docker-compose.yml logs --tail=200 n8n n8n-runner postgres
docker compose --env-file .env -f docker-compose.yml up -d --wait
```

O acesso bootstrap fica em
`/opt/automacao_grupo_compras/n8n/bootstrap-owner.txt`, com modo `0600`.
Trocar email e senha no primeiro acesso e remover esse arquivo depois da
rotacao.

### Backup e rollback da instalacao anterior

O backup verificado da instalacao anterior esta em
`/opt/automacao_grupo_compras/backups/legacy-n8n/20260808T220448Z` e inclui
configuracao, volume e `SHA256SUMS`. O projeto antigo em `/docker/n8n-owco`
permanece parado, sem remocao do volume.

Para rollback:

1. Desativar a label Traefik da stack nova e recriar o servico `n8n`.
2. Subir `/docker/n8n-owco/docker-compose.yml` com o project directory
   `/docker/n8n-owco`.
3. Validar `/healthz` pelo dominio HTTPS.
4. Nao usar `down -v` em nenhuma das stacks.

Checklist antes de instalar/configurar n8n:

1. Confirmar IP/host da VPS Hostinger, usuario SSH e porta.
2. Criar ou selecionar chave SSH local para VSCode Remote SSH.
3. Registrar a chave publica no painel/servidor da Hostinger.
4. Conectar no VSCode Remote SSH.
5. Validar persistencia da VPS antes de subir o n8n.
6. Configurar n8n com armazenamento persistente e credenciais fora do Git.
7. Importar `n8n/workflows/ofertas-mvp-supabase.json`.
8. Rodar primeiro teste com `dry_run=true`.

### VSCode/Codex para VPS

O acesso recomendado e VSCode Remote SSH usando chave local.

Objetivo:

- abrir a VPS como ambiente remoto;
- criar ou editar arquivos operacionais no servidor;
- manter segredos fora do repositorio;
- evitar copiar artefatos manualmente entre PC local e servidor.

O repositorio continua sendo a fonte versionada. Arquivos com segredo, sessoes,
tokens, QR codes ou credenciais ficam apenas na VPS ou no painel seguro do
servico correspondente.

### Codex para n8n

Codex nao deve depender de acesso direto ao painel do n8n para gerar a primeira
versao do fluxo.

O caminho inicial recomendado e:

- versionar no repositorio um workflow exportavel;
- importar esse workflow no n8n;
- configurar credenciais e destinos manualmente no painel do n8n;
- validar o fluxo em `dry_run=true` antes de qualquer envio real.

Se houver necessidade de operar o painel, o acesso deve acontecer por sessao
autorizada pelo operador, sem registrar credenciais no Git.

### n8n para Supabase

O n8n precisa de credencial segura para:

- consultar `offers.v_offer_ranking_current`;
- registrar eventos em `offers.publication_events`.

Essa credencial deve ficar configurada no proprio n8n. Ela nao deve aparecer em
workflow versionado, arquivo `.env` commitado, print, log publico ou documento
do repositorio.

Na validacao de 2026-08-09, a credencial foi criada como credencial `Postgres`
do n8n, apontando para o Postgres do Supabase. Para o pooler do Supabase, o
campo SSL precisou ficar em `require` com `Ignore SSL Issues (Insecure)`
habilitado, pois apenas `allow`/`require`/`disable` sem ignorar a cadeia gerou
erro de certificado autoassinado na cadeia.

Essa configuracao desbloqueia o MVP mantendo transporte criptografado, mas
ainda nao e o estado ideal de seguranca porque desabilita validacao completa da
cadeia TLS. Endurecimento futuro: configurar CA confiavel no container/n8n ou
ajustar a credencial quando a UI permitir fornecer o certificado CA.

Validacao minima dessa conexao:

1. consultar `offers.v_offer_ranking_current` com `profile`, `marketplace` e
   `limit` explicitos;
2. montar `message_text` com disclosure;
3. registrar um evento de `dry_run` ou bloqueio em
   `offers.publication_events`;
4. repetir o mesmo registro e confirmar que a idempotencia nao duplica a linha.

## Etapa 1: pacote versionado

Arquivo importavel:

- [`n8n/workflows/ofertas-mvp-supabase.json`](../n8n/workflows/ofertas-mvp-supabase.json)

Payload seguro de referencia:

- [`n8n/payloads/ofertas-mvp-supabase-context.example.json`](../n8n/payloads/ofertas-mvp-supabase-context.example.json)

Objetivo desta etapa:

- validar o fluxo MVP sem depender de VPS, Cloud Run, Google Sheets ou runner
  HTTP;
- manter `dry_run=true` como padrao;
- consultar o ranking atual no Supabase;
- montar uma mensagem minima com disclosure;
- bloquear destinos fora da allowlist;
- registrar a tentativa ou bloqueio em `offers.publication_events`.

### Como importar

1. Abrir o n8n.
2. Importar `n8n/workflows/ofertas-mvp-supabase.json`.
3. Criar ou selecionar uma credencial Postgres apontando para o Supabase.
4. Associar essa credencial aos nodes:
   - `Consultar Ranking Supabase`;
   - `Registrar Resultado Supabase`.
5. Confirmar que o workflow permanece inativo ate o teste manual controlado.
6. Se os nodes `Set` importarem com output vazio, substituir manualmente por
   nodes `Code` preservando os nomes:
   - `Set Contexto MVP`;
   - `Simular Envio MVP`.

Credenciais reais devem ficar apenas no painel do n8n. O arquivo exportado do
workflow pode referenciar o nome logico da credencial, mas nao deve carregar
host privado, usuario, senha, service role key, token ou cookie.

### Observacao de compatibilidade da importacao

Na instancia `n8n` 2.32.6 da VPS, os nodes `Set` do workflow importado
produziram output vazio (`[{}]`) durante o teste manual. O contorno operacional
foi substituir esses nodes por `Code` nodes diretamente no painel:

- `Set Contexto MVP`: preenche `dry_run`, `limit`, `profile`, `marketplace`,
  `target`, `allowed_targets_csv`, `channel_adapter` e `run_id`;
- `Simular Envio MVP`: preserva o item recebido e adiciona `send_result` e
  `sent_at`.

O arquivo versionado `n8n/workflows/ofertas-mvp-supabase.json` ainda deve ser
atualizado para refletir essa correcao e evitar que uma nova importacao repita
o problema.

### Teste controlado

Executar com o contexto minimo:

```json
{
  "profile": "feminino",
  "marketplace": "shopee",
  "limit": 1,
  "target": "teste-whatsapp",
  "allowed_targets_csv": "teste-whatsapp",
  "channel_adapter": "whatsapp",
  "dry_run": true,
  "artifact_generated_at": "2026-07-18T00:00:00.000Z",
  "run_id": "manual-YYYY-MM-DD-001"
}
```

Resultado esperado:

- a query retorna no maximo 1 oferta elegivel;
- `message_text` contem produto, preco, avaliacao, link e disclosure;
- `send_result` fica como `dry_run_not_sent`;
- `delivery_status` fica como `cancelled`, porque nao houve envio real;
- uma linha e registrada em `offers.publication_events`.

### Teste de bloqueio

Repetir o teste com:

```json
{
  "target": "destino-nao-permitido",
  "allowed_targets_csv": "teste-whatsapp"
}
```

Resultado esperado:

- o envio e bloqueado antes de qualquer node de canal real;
- `blocked_reason` fica como `target_not_allowlisted`;
- o bloqueio tambem e registrado em `offers.publication_events`.

### Teste de idempotencia

Reexecutar o mesmo teste mantendo iguais:

- `profile`;
- `target`;
- `manifest_item_number`;
- `artifact_generated_at`.

Resultado esperado:

- o `on conflict` atualiza a linha existente;
- `publish_id` permanece o mesmo;
- nao surge uma segunda publicacao para a mesma mensagem da rodada.

## Query MVP

O node do Supabase deve consultar:

```sql
select
  profile,
  marketplace,
  stable_key,
  item_id,
  product_name,
  offer_link,
  price,
  reference_price,
  rating,
  sales_count,
  primary_subniche,
  commercial_score,
  score_reasons,
  rank_profile,
  rank_subniche
from offers.v_offer_ranking_current
where is_eligible = true
  and profile = :profile
  and marketplace = :marketplace
order by
  rank_profile nulls last,
  commercial_score desc,
  sales_count desc,
  rating desc nulls last,
  item_id
limit :limit;
```

Regra: nao adicionar filtros escondidos. Qualquer filtro novo precisa aparecer
no workflow e na documentacao.

## Template minimo

O n8n deve montar `message_text` com os campos da query.

Template minimo:

```text
{{product_name}}

Preco: R$ {{price}}
Avaliacao: {{rating}}

Link: {{offer_link}}

Aviso: este link pode gerar comissao de afiliado. Preco e disponibilidade
podem mudar.
```

## Allowlist

Antes de qualquer envio real, o workflow deve verificar:

- `target` existe na allowlist;
- canal do target esta ativo;
- `dry_run` esta coerente com a etapa da rodada.

Se o destino nao estiver na allowlist, o workflow deve bloquear o envio e
registrar o bloqueio como resultado da rodada.

## Registro em publication_events

Apos tentativa de envio, o n8n deve gravar em `offers.publication_events`:

- `profile`;
- `marketplace`;
- `stable_key`;
- `item_id`;
- `target`;
- `channel_adapter`;
- `delivery_status`;
- `manifest_item_number`;
- `artifact_generated_at`;
- `sent_at`;
- `offer_title`;
- `offer_url`;
- `offer_price`;
- `message_text`;
- `payload`.

Retries nao devem duplicar publicacao. A chave operacional documentada em
[`supabase-publication-events.md`](supabase-publication-events.md) deve ser
preservada.

## Validacao minima

1. Rodar a query para 1 profile e confirmar ofertas elegiveis.
2. Rodar o workflow em `dry_run=true` para 1 destino allowlisted.
3. Testar destino fora da allowlist e confirmar bloqueio.
4. Rodar envio controlado para 1 destino allowlisted.
5. Registrar o resultado em `publication_events`.
6. Repetir o mesmo registro e confirmar que nao duplica.

## Resultado do primeiro dry-run manual

Validacao manual realizada em 2026-08-09:

- contexto efetivo:
  - `dry_run=true`;
  - `limit=1`;
  - `profile=feminino`;
  - `marketplace=shopee`;
  - `target=teste-whatsapp`;
  - `allowed_targets_csv=teste-whatsapp`;
  - `channel_adapter=whatsapp`;
- query executada contra `offers.v_offer_ranking_current`;
- oferta retornada:
  - `item_id=58211202356`;
  - `offer_title=Bolsa Feminina Clutch De Ombro Pequena Sofisticada Alça Regulável`;
  - `offer_price=16.99`;
  - `rank_profile=1`;
  - `rank_subniche=1`;
- registro criado em `offers.publication_events`:
  - `publish_id=461e54bf-aff6-4907-870d-3eedc15d047d`;
  - `delivery_status=cancelled`;
  - `payload.dry_run=true`;
  - `payload.send_result=dry_run_not_sent`;
  - `payload.target_allowed=true`;
  - `payload.blocked_reason=null`.

Esse resultado confirma consulta, montagem de mensagem, allowlist e auditoria em
modo dry-run. O workflow deve permanecer inativo ate a correcao versionada dos
nodes importados e novo dry-run limpo.

## Fora do MVP

- Cloud Run.
- Runner HTTP.
- Revisao humana item a item.
- Coleta automatica do catalogo.
- Revisao completa dos nichos.
- Roteamento complexo por multiplos grupos.

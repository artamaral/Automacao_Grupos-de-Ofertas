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
  -> Simular envio logico
  -> Preparar envio WAHA
  -> Enviar imagem + legenda WhatsApp WAHA quando dry_run=false e target allowlisted
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
- `target_chat_id` opcional: chat id WAHA explicito. Se ausente, o workflow
  tenta normalizar `target` para `${digits}@c.us`.
- `coupon_url` opcional: URL de cupom usada no template Shopee. Se ausente, o
  workflow usa a URL global versionada em `config/coupon_urls.toml`.

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

### Implantacao WAHA na VPS

Estado implantado em 2026-08-09:

- servico `waha` adicionado ao Compose operacional em
  `/opt/automacao_grupo_compras/n8n/docker-compose.yml`;
- imagem: `devlikeapro/waha`;
- porta publicada somente em `127.0.0.1:3000`;
- volume persistente de sessao:
  `/opt/automacao_grupo_compras/n8n/data/waha/.sessions`;
- API protegida por `X-Api-Key`;
- valor hash da API key no `.env`; valor plain apenas em
  `/opt/automacao_grupo_compras/n8n/waha-operator.txt` com modo `0600`;
- dashboard e Swagger protegidos por credenciais locais no `.env`;
- `health` e `ping` liberados sem API key para healthcheck;
- sessao `default` criada, pareada e conectada;
- status atual esperado: `WORKING` / `CONNECTED`.

Base URL para o n8n:

```text
http://waha:3000
```

Base URL local na VPS:

```text
http://127.0.0.1:3000
```

Para acessar o dashboard sem expor a API publicamente, abrir tunel SSH local:

```bash
ssh -L 3000:127.0.0.1:3000 <usuario>@<host-da-vps>
```

Depois abrir no navegador local:

```text
http://127.0.0.1:3000/dashboard
```

Usar as credenciais de `/opt/automacao_grupo_compras/n8n/waha-operator.txt`.
Esse arquivo nao deve ser copiado para o repositorio.

#### Conexao do dashboard WAHA

O dashboard tem duas camadas de credencial:

- usuario/senha do dashboard: apenas abre a interface web;
- `X-Api-Key`: autoriza as chamadas da interface para a API WAHA.

Ao abrir o dashboard pelo tunel local, configurar a conexao do servidor como:

```text
WAHA VPS URL: http://127.0.0.1:3000
```

Nao incluir `/dashboard` nesse campo.

No campo de API key, usar o valor plain da linha `X-Api-Key:` do arquivo
operacional:

```text
/opt/automacao_grupo_compras/n8n/waha-operator.txt
```

Esse valor nao deve ser colado em issues, logs, mensagens, commits ou docs.

Se o dashboard mostrar:

```text
Server connection failed
WAHA VPS (http://127.0.0.1:3000) is not connected.
Please make sure it's online and set right API key in the configuration.
```

validar na ordem:

1. manter o tunel SSH aberto no computador local:

```bash
ssh -N -L 3000:127.0.0.1:3000 <usuario>@<host-da-vps>
```

2. abrir no navegador local:

```text
http://127.0.0.1:3000/health
```

3. confirmar que o retorno contem `status: ok`;
4. voltar ao dashboard e conferir se a URL esta como
   `http://127.0.0.1:3000`;
5. conferir se a API key usada no dashboard e o valor de `X-Api-Key`, nao a
   senha do dashboard.

Se `/health` responder `status: ok`, o tunel e o servico estao acessiveis pelo
navegador. Nesse caso, a causa mais provavel do erro e API key ausente ou
incorreta na configuracao do dashboard.

Para verificar a sessao pela VPS sem depender do dashboard:

```bash
cd /opt/automacao_grupo_compras/n8n
WAHA_KEY=$(awk -F': ' '/^X-Api-Key:/ {print $2}' waha-operator.txt)
curl -fsSL -H "X-Api-Key: ${WAHA_KEY}" \
  http://127.0.0.1:3000/api/sessions/default
```

Estado esperado para a sessao principal:

```text
name: default
status: WORKING
engine.state: CONNECTED
```

### Acoplamento WAHA no workflow

O workflow `ofertas-mvp-supabase` chama a WAHA somente depois de:

- ranking consultar uma oferta elegivel ainda nao confirmada para o mesmo
  `target` e `channel_adapter`;
- ranking retornar `image_url` publica valida;
- allowlist aprovar o destino;
- `dry_run` ser `false`;
- `send_result` estar como `ready_for_real_channel_node`.

Nodes WAHA no workflow:

```text
Simular Envio MVP
  -> Preparar Envio WAHA
  -> IF Pode Enviar WAHA
     -> true: Enviar WhatsApp WAHA -> Normalizar Resultado WAHA
     -> false: Montar Upsert Publication Event
  -> Montar Upsert Publication Event
  -> Registrar Resultado Supabase
```

Configuracao esperada do node `Enviar WhatsApp WAHA`:

- metodo: `POST`;
- URL: `http://waha:3000/api/sendImage`;
- autenticacao: credencial n8n `WAHA Header Auth` do tipo `httpHeaderAuth`;
- body JSON:

```javascript
JSON.stringify({
  session: 'default',
  chatId: $json.waha_chat_id,
  file: {
    mimetype: 'image/jpeg',
    url: $json.waha_image_url,
    filename: $json.waha_image_filename || 'oferta.jpg',
  },
  caption: $json.message_text,
})
```

O node `Normalizar Resultado WAHA` registra no payload:

- `adapter_status`;
- `adapter_message_id`;
- `adapter_ack`;
- `adapter_response_type`.

O node `Preparar Envio WAHA` bloqueia envio real com
`adapter_missing_image_url` quando `image_url` estiver ausente ou nao for uma
URL `http(s)`. O bloqueio e registrado no Supabase como `delivery_status =
failed`, sem chamar a WAHA.

### Envio manual para grupo WhatsApp

Para enviar para um grupo, o workflow usa dois conceitos separados:

- `target`: nome logico versionado/auditavel do destino;
- `target_chat_id`: id real do chat WAHA, normalmente terminado em `@g.us`.

O `target` precisa estar autorizado por `allowed_targets_csv`. O
`target_chat_id`, quando informado, substitui o `target` somente no envio para a
WAHA. Assim o log continua usando o nome logico, enquanto o adapter recebe o id
real do grupo.

Exemplo de `pinData` para execucao manual controlada:

```json
{
  "Trigger Manual": [
    {
      "json": {
        "dry_run": false,
        "limit": 1,
        "profile": "feminino",
        "marketplace": "shopee",
        "target": "grupo-ofertas-feminino",
        "target_chat_id": "120363XXXXXXXXXXXX@g.us",
        "allowed_targets_csv": "grupo-ofertas-feminino",
        "channel_adapter": "whatsapp"
      }
    }
  ]
}
```

Checklist antes de executar manualmente para grupo:

1. confirmar que o grupo e opt-in;
2. obter o `chatId` real do grupo no WAHA;
3. usar um `target` logico claro e estavel;
4. incluir o mesmo `target` em `allowed_targets_csv`;
5. manter `limit=1` no primeiro teste;
6. restaurar `dry_run=true` e o destino de teste apos a execucao.

Para descobrir grupos pela API WAHA, com a sessao `default` conectada, consultar
os endpoints disponiveis no Swagger local:

```text
http://127.0.0.1:3000/swagger
```

ou no JSON da especificacao:

```bash
cd /opt/automacao_grupo_compras/n8n
WAHA_KEY=$(awk -F': ' '/^X-Api-Key:/ {print $2}' waha-operator.txt)
curl -fsSL -H "X-Api-Key: ${WAHA_KEY}" \
  http://127.0.0.1:3000/api-docs-json
```

O id usado pelo n8n deve ser o chat id do grupo, nao o nome exibido do grupo.

### Template Shopee

O node `Montar Mensagens` deve seguir o template Shopee oficial versionado em
[`config/message_templates/shopee.txt`](../config/message_templates/shopee.txt).

Formato esperado:

```text
🔥 {{facts.title}}

🏪 Loja: {{facts.marketplace}}

💵 {{facts.price | brl}}

🏷️ {{facts.discount_percent | round}}% OFF

⭐ Avaliação: {{facts.rating | rating_br}}/5

🎟️ Resgate o cupom desta página:
{{coupon_url}}

✅ Link do produto:
{{facts.url}}

(anúncio)
```

Mapeamento atual do n8n:

- `facts.title`: `product_name`;
- `facts.marketplace`: `marketplace`, formatado como `Shopee` quando
  `marketplace = shopee`;
- `facts.price`: `price`, formatado em BRL;
- `facts.discount_percent`: calculado a partir de `reference_price` e `price`;
- `facts.rating`: `rating`;
- `facts.url`: `offer_link`;
- `coupon_url`: entrada opcional do workflow ou URL global versionada em
  `config/coupon_urls.toml`.

O antigo template minimo do MVP foi mantido apenas como historico dos dry-runs
iniciais. Novos envios devem usar o template Shopee acima, com `(anúncio)` como
marcador explicito de publicidade/afiliado.

### Teste real controlado

Manter o workflow inativo e executar manualmente com destino controlado:

```json
{
  "dry_run": false,
  "limit": 1,
  "profile": "feminino",
  "marketplace": "shopee",
  "target": "55DDDNUMERO",
  "allowed_targets_csv": "55DDDNUMERO",
  "channel_adapter": "whatsapp"
}
```

Validar no Supabase:

```sql
select
  publish_id,
  target,
  delivery_status,
  sent_at,
  payload->>'send_result' as send_result,
  payload->>'adapter_status' as adapter_status,
  payload->>'adapter_message_id' as adapter_message_id,
  payload->>'waha_image_url' as waha_image_url,
  created_at
from offers.publication_events
where target = '55DDDNUMERO'
order by created_at desc
limit 5;
```

Resultado esperado: `delivery_status = confirmed`,
`send_result = sent_to_adapter`, `adapter_status = sent_to_adapter` e envio
recebido no WhatsApp de teste como imagem com legenda.

Ultimo teste real validado em 2026-08-09:

- workflow executado manualmente pelo n8n com `dry_run=false`, `limit=1` e
  destino explicitamente allowlisted;
- execucao n8n: `23`;
- WAHA: `POST /api/sendText` com HTTP 201;
- `delivery_status`: `confirmed`;
- `send_result`: `sent_to_adapter`;
- `adapter_status`: `sent_to_adapter`;
- `publish_id`: `1e99a91a-9684-4e69-9024-f0c4ae0ea0f3`;
- oferta enviada: `58211202356`;
- workflow permaneceu inativo e o `pinData` foi restaurado para `dry_run=true`
  depois do teste.

Observacao: esse teste validou a integracao n8n -> WAHA -> Supabase usando o
template minimo anterior. Apos a validacao de canal, o workflow foi alinhado ao
template Shopee oficial documentado acima. Em seguida, o workflow foi ajustado
para enviar `image_url` via `POST /api/sendImage`, usando `message_text` como
legenda.

Observacao operacional: neste ambiente o n8n roda com task runners externos.
Evitar `n8n execute --id ...` dentro do container principal para testes reais,
pois a CLI tenta abrir um broker proprio e pode falhar antes dos nodes `Code`.
Executar testes controlados pelo painel ou pela API REST local da instancia
n8n ja em execucao.

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
docker compose --env-file .env -f docker-compose.yml logs --tail=200 waha
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
6. Conferir que `Set Contexto MVP` e `Simular Envio MVP` estao como nodes
   `Code`.

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

O arquivo versionado `n8n/workflows/ofertas-mvp-supabase.json` ja foi
atualizado para refletir essa correcao. Novas importacoes devem preservar esses
dois nodes como `Code`.

### Deploy guard do workflow

Antes de testar envios reais, reaplicar e validar o workflow versionado com:

```bash
python3 scripts/n8n/deploy_workflow_guard.py --mode grupo-real
```

Esse comando atualiza o workflow `OfertasMvpSupab1` diretamente no banco do
n8n a partir de `n8n/workflows/ofertas-mvp-supabase.json`, mantendo
`active=false` e validando:

- existe `/api/sendImage`;
- nao existe `/api/sendText`;
- o template contem `Resgate o cupom desta página`;
- o `pinData` esta pronto para execucao manual do grupo real com
  `dry_run=false`, `limit=1` e `target_chat_id` terminado em `@g.us`.

Modos operacionais:

- `grupo-real`: prepara envio real para `grupo-ofertas-feminino`;
- `teste-telefone`: prepara envio real para o telefone de teste
  `5511975235421`;
- `dry-run`: prepara `dry_run=true` com `target=teste-whatsapp`;
- `preserve-pindata`: reaplica o workflow sem alterar `pinData`.

Para validar sem alterar o n8n:

```bash
python3 scripts/n8n/deploy_workflow_guard.py --dry-run --mode grupo-real
```

Modos alternativos:

```bash
python3 scripts/n8n/deploy_workflow_guard.py --safe-pindata
python3 scripts/n8n/deploy_workflow_guard.py --preserve-pindata
```

`--safe-pindata` deixa `dry_run=true` e `target=teste-whatsapp`. Essa flag e
mantida por compatibilidade; preferir `--mode dry-run` em novos comandos.
`--preserve-pindata` e equivalente a `--mode preserve-pindata`.

Se uma aba antiga do editor n8n estiver aberta, ela pode salvar uma versao
antiga por cima do workflow correto. Antes de executar testes reais:

1. fechar abas antigas do workflow;
2. rodar o deploy guard;
3. abrir o workflow novamente pela lista do n8n;
4. executar manualmente;
5. conferir no log da WAHA se houve `POST /api/sendImage`.

### Checklist operacional por rodada

Comando principal:

```bash
python3 scripts/n8n/run_operational_round.py --mode teste-telefone
```

O wrapper executa, em ordem:

1. `deploy_workflow_guard.py --mode <mode>`;
2. `run_workflow_manual.py --mode <mode>`;
3. `check_last_execution.py`.

Modos aceitos:

- `teste-telefone`: envio real controlado para o telefone de teste;
- `grupo-real`: envio real controlado para o grupo allowlisted;
- `dry-run`: sem envio real.

Nos modos `grupo-real` e `teste-telefone`, a checagem final usa
`--expect-real-image`. No modo `dry-run`, ela nao exige
`adapter_response_type=image`.

O wrapper para no primeiro erro e imprime resumo final com `execution_id`,
`endpoint`, `publish_id`, `delivery_status`, `adapter_response_type` e
`copy_template`. Linhas contendo senha, cookie, token ou API key sao redigidas
antes de serem impressas.

Rodada manual pelo painel n8n:

```bash
python3 scripts/n8n/deploy_workflow_guard.py --mode grupo-real
```

Confirmar WAHA:

```bash
cd /opt/automacao_grupo_compras/n8n
WAHA_KEY=$(awk -F': ' '/^X-Api-Key:/ {print $2}' waha-operator.txt)
curl -fsSL -H "X-Api-Key: ${WAHA_KEY}" \
  http://127.0.0.1:3000/api/sessions/default
```

Estado esperado: `WORKING` / `CONNECTED`.

Depois executar manualmente no painel n8n e checar:

```bash
python3 scripts/n8n/check_last_execution.py --expect-real-image
```

Resultado esperado:

```text
status=success
endpoint=sendImage
delivery_status=confirmed
adapter_response_type=image
copy_template=novo
publish_id=<uuid>
```

Para reduzir dependencia do painel e de abas antigas do editor, executar via
API local do n8n:

```bash
python3 scripts/n8n/deploy_workflow_guard.py --mode grupo-real
python3 scripts/n8n/run_workflow_manual.py --mode grupo-real
python3 scripts/n8n/check_last_execution.py --expect-real-image
```

O script `run_workflow_manual.py` exige `--mode` explicitamente. Ele atualiza o
`pinData`, autentica no n8n usando
`/opt/automacao_grupo_compras/n8n/bootstrap-owner.txt` e chama
`POST /rest/workflows/OfertasMvpSupab1/run` ate o node
`Registrar Resultado Supabase`. O script usa a URL HTTPS publica do n8n por
padrao, porque o cookie `n8n-auth` e seguro e nao e reenviado em chamadas HTTP
locais. O script nao imprime senha, cookie ou token.

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
from offers.v_offer_ranking_current ranking
where ranking.is_eligible = true
  and ranking.profile = :profile
  and ranking.marketplace = :marketplace
  and not exists (
    select 1
    from offers.publication_events event
    where event.profile = ranking.profile
      and event.marketplace = ranking.marketplace
      and event.stable_key = ranking.stable_key
      and event.target = :target
      and event.channel_adapter = :channel_adapter
      and event.delivery_status = 'confirmed'
  )
order by
  rank_profile nulls last,
  commercial_score desc,
  sales_count desc,
  rating desc nulls last,
  item_id
limit :limit;
```

Regra: `delivery_status = 'confirmed'` bloqueia nova selecao do mesmo
`stable_key` para o mesmo `target` e `channel_adapter`. Registros `cancelled`,
incluindo dry-run e bloqueio por allowlist, nao retiram a oferta do ranking
futuro.

Nao adicionar filtros escondidos. Qualquer filtro novo precisa aparecer no
workflow e na documentacao.

## Template historico do dry-run inicial

O primeiro dry-run do MVP usou o formato minimo abaixo para validar consulta,
allowlist e auditoria. Ele nao e mais o padrao para novos envios Shopee.

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

Esse resultado confirmou consulta, montagem de mensagem, allowlist e auditoria
em modo dry-run. Depois da correcao dos nodes `Code`, tambem foram validados:

- `sent_at = null` em dry-run;
- idempotencia sem duplicatas;
- anti-repost para ofertas ja confirmadas no mesmo `target` e
  `channel_adapter`;
- teste logico com `dry_run=false`, registrando
  `send_result=ready_for_real_channel_node`.

O workflow deve permanecer inativo ate o node real WAHA ser acoplado e passar
por teste minimo controlado com allowlist.

## Fora do MVP

- Cloud Run.
- Runner HTTP.
- Revisao humana item a item.
- Coleta automatica do catalogo.
- Revisao completa dos nichos.
- Roteamento complexo por multiplos grupos.

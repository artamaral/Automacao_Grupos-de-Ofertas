# Serviço assíncrono de renderização de Reels

## Contrato

O renderer fica na rede interna Docker do Traefik. Ele não recebe rota pública;
somente o Nginx entrega os MP4s concluídos em `/media/jobs/`.

### Criar ou recuperar um job

```http
POST /v1/render/jobs
Authorization: Bearer <REELS_RENDER_API_TOKEN>
Content-Type: application/json
```

Payload mínimo:

```json
{
  "job_id": "dispatch-20260920-item-23098338263",
  "item_id": "23098338263",
  "planned_date": "2026-09-20",
  "source_dispatch_plan_id": "uuid-do-plano",
  "video_url": "https://cdn.allowlisted.example/source.mp4",
  "price": "R$ 39,97",
  "template_id": 3,
  "ass_template": "conteudo ASS lido do Google Drive"
}
```

O endpoint responde `202 Accepted`. Repetir o mesmo `job_id` com o mesmo
payload é idempotente; reutilizar o `job_id` com payload diferente responde
`409 Conflict`.

### Consultar status

```http
GET /v1/render/jobs/{job_id}
Authorization: Bearer <REELS_RENDER_API_TOKEN>
```

Estados esperados: `queued`, `running`, `succeeded` ou `failed` com
`render_status=failed_fallback_original`. No último caso, o n8n publica o
`video_url` original.

O renderer tenta no máximo duas vezes. Os erros retornados são limitados e
sanitizados; não devem conter tokens, headers, URLs assinadas ou caminhos
internos.

## Configuração obrigatória

No `.env` da VPS, fora do Git:

```dotenv
REELS_RENDER_API_TOKEN=token-opaco-longo
REELS_PUBLIC_BASE_URL=https://n8n-owco.srv1805131.hstgr.cloud/media/jobs
REELS_SOURCE_HOST_ALLOWLIST=susercontent.com,susercontent.com.br,shopee.com.br
```

Também são configuráveis `REELS_MAX_SOURCE_BYTES`,
`REELS_MAX_DURATION_SECONDS`, `REELS_RENDER_TIMEOUT_SECONDS` e
`REELS_MAX_CONCURRENT`. Os valores atuais são guardrails iniciais, não limites
de produção aprovados; devem ser calibrados no teste de carga.

## Deploy na VPS

Na pasta da stack:

```bash
docker compose build reels-renderer
docker compose up -d reels-renderer reels-media
docker compose ps
curl -fsS http://127.0.0.1:8080/healthz
```

O estado interno fica em `/opt/automacao_grupo_compras/reels-render-state`.
Somente `output.mp4` fica em `/opt/automacao_grupo_compras/media/jobs`, que é a
pasta pública do Nginx. `metadata.json`, origem baixada e ASS temporário não
são publicados.

## Ainda necessário antes de produção

- configurar o token e a allowlist real dos CDNs Shopee;
- conectar os nós n8n de criação/consulta do job;
- medir limites de duração, tamanho, concorrência, memória e timeout;
- implementar limpeza protegida dos jobs concluídos;
- validar o registro de `template_id`, `artifact_url`, tentativas e erros no
  `offers.publication_events` existente.

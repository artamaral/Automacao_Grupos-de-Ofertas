# Estado atual do n8n OfertasMvpSupab1 antes de incluir canal

Data do levantamento: 2026-08-25.

Este documento registra o estado observado antes de qualquer alteracao para
enviar tambem a um canal WhatsApp via WAHA. O levantamento comparou:

- workflow versionado em `n8n/workflows/ofertas-mvp-supabase.json`;
- workflow efetivo no n8n da VPS `hostinger-n8n`, lido em modo somente leitura
  a partir do banco do n8n.

Nenhum deploy, importacao, ativacao ou envio foi executado durante este
levantamento.

## Workflow efetivo na VPS

Workflow:

- id: `OfertasMvpSupab1`;
- name: `ofertas-mvp-supabase`;
- active: `true`;
- versionCounter: `173`;
- updatedAt: `2026-08-22T20:39:34.798+00:00`;
- nodes: `75`.

O estado efetivo esta ativo no painel do n8n. Isso difere do comportamento do
guard de deploy, que preserva o workflow importado como `active=false`.

## Fluxos existentes

O workflow possui tres fluxos que enviam pelo WAHA e devem ser tratados juntos
em qualquer alteracao de destino:

1. Fluxo recorrente do catalogo Supabase.
   - Schedule: `Schedule Grupo Real`.
   - Envio: `Enviar WhatsApp WAHA`.
   - Midia: `file.url` com `image_url`.
   - Destino atual: `grupo-ofertas-feminino`.

2. Fluxo de mensagens estaticas.
   - Schedule: `Schedule Mensagens Estaticas`.
   - Envio: `Enviar WhatsApp WAHA Estatico`.
   - Midia: `file.data` com `image.jpg` em base64.
   - Destino atual: `grupo-ofertas-feminino`.

3. Fluxo de mensagens pontuais.
   - Schedule: `Schedule Mensagens Pontuais`.
   - Envio: `Enviar WhatsApp WAHA Pontual`.
   - Midia: `file.data` com `image.jpg` em base64.
   - Destino atual: `grupo-ofertas-feminino`.

## Crons efetivos na VPS

Estado observado no n8n vivo:

```text
Schedule Grupo Real          | 0 8-21 * * *
Schedule Mensagens Estaticas | 30 9 * * * ; 30 17 * * *
Schedule Mensagens Pontuais  | 45 17 * * * ; 46 17 * * * ; 47 17 * * * ; 48 17 * * *
```

## Crons versionados no repositorio

Estado em `n8n/workflows/ofertas-mvp-supabase.json` apos reconciliacao local
feita em 2026-08-25:

```text
Schedule Grupo Real          | 0 8-21 * * *
Schedule Mensagens Estaticas | 30 9 * * * ; 30 17 * * *
Schedule Mensagens Pontuais  | 45 17 * * * ; 46 17 * * * ; 47 17 * * * ; 48 17 * * *
```

## Divergencias relevantes

As divergencias conhecidas entre o efetivo da VPS e o versionado local apos a
reconciliacao dos crons sao:

- o n8n efetivo esta `active=true`, enquanto o guard de deploy deixa o workflow
  como `active=false`;
- os crons efetivos da VPS foram versionados localmente para evitar que um
  deploy futuro volte aos horarios antigos.

A diferenca de ativacao continua deliberada: o versionado local permanece
inativo por seguranca e a ativacao no painel segue como uma fronteira
operacional separada.

## Destino atual

Os tres fluxos estao hardcoded para o mesmo destino logico e o mesmo chat WAHA:

```text
target: grupo-ofertas-feminino
target_chat_id: 120363412864266334@g.us
allowed_targets: grupo-ofertas-feminino
channel_adapter: whatsapp
```

Nao foi observado destino de canal WhatsApp no workflow efetivo. Tambem nao foi
observado `chatId` no formato `@newsletter`.

## Nos WAHA atuais

Todos os envios usam o mesmo endpoint:

```text
http://waha:3000/api/sendImage
```

Nos atuais:

- `Enviar WhatsApp WAHA`;
- `Enviar WhatsApp WAHA Estatico`;
- `Enviar WhatsApp WAHA Pontual`.

Todos os tres usam autenticacao via credencial do n8n e sessao WAHA `default`.

## PinData efetivo

O `pinData` efetivo observado aponta para envio real ao grupo:

```json
{
  "dry_run": false,
  "limit": 8,
  "profile": "feminino",
  "marketplace": "shopee",
  "target": "grupo-ofertas-feminino",
  "target_chat_id": "120363412864266334@g.us",
  "allowed_targets_csv": "grupo-ofertas-feminino",
  "channel_adapter": "whatsapp",
  "send_delay_seconds_min": 45,
  "send_delay_seconds_max": 90
}
```

## Guard local atual

O guard local `scripts/n8n/deploy_workflow_guard.py` ainda protege o destino
atual do grupo:

- espera `target_chat_id` real terminando em `@g.us` ou `@c.us` para pinData de
  envio real;
- valida `EXPECTED_STATIC_TARGET = grupo-ofertas-feminino`;
- valida `EXPECTED_STATIC_CHAT_ID = 120363412864266334@g.us`;
- rejeita mudanca do chat id dos fluxos estatico e pontual nos testes atuais;
- exige `/api/sendImage` e ausencia de `/api/sendText`.

Para incluir um canal WhatsApp, o guard precisara ser atualizado de forma
explicita para aceitar `@newsletter` e validar a nova topologia dos tres
fluxos.

## Implicacao para a proxima mudanca

A inclusao de canal nao deve ser aplicada em apenas um ponto do workflow. A
mudanca precisa cobrir os tres fluxos:

- recorrente Supabase;
- mensagens estaticas;
- mensagens pontuais.

O desenho recomendado e uma expansao controlada de destinos depois que a
mensagem ja estiver montada:

```text
mensagem pronta
  -> destino grupo
  -> destino canal
  -> valida allowlist por destino
  -> envia WAHA por destino
  -> registra publication_events por destino
```

Isso evita rodar duas selecoes independentes da mesma oferta e reduz o risco de
o cooldown/publication state bloquear o segundo destino.

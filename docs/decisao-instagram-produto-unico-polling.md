# Decisão — produto único por publicação Instagram e retry de container

## Status

Decisão vigente a partir de 2026-08-23 para o workflow `ofertas-instagram-supabase`.

Este documento complementa `docs/spec-instagram-reels-carousel.md`. As demais regras da spec permanecem inalteradas.

## 1. Objetivo

Corrigir dois comportamentos observados durante a validação real do Instagram:

1. impedir que o mesmo item confirmado seja reutilizado no outro formato Instagram no mesmo dia;
2. corrigir o retry do polling de processamento do container, que estava encerrando a execução na primeira tentativa mesmo com `poll_attempt = 1`.

Não alterar WhatsApp, ranking, taxonomia, copy, schedule, credenciais ou versão da Graph API.

## 2. Produto único entre Reels e Carrossel

A alternância diária continua sendo:

```text
Reels → Carrossel → Reels → Carrossel → Reels → Carrossel
```

A contagem continua usando somente publicações Instagram com:

```text
delivery_status = confirmed
```

Além da alternância de formato, cada publicação Instagram confirmada do dia deve utilizar um `source_dispatch_plan_id` diferente.

Portanto, depois que um `dispatch_plan_id` for confirmado em qualquer um dos canais:

```text
instagram_reels
instagram_carousel
```

esse mesmo `dispatch_plan_id` deixa de ser elegível para qualquer publicação Instagram posterior no mesmo dia, independentemente do formato seguinte.

A exclusão deve considerar somente eventos reais confirmados:

```text
delivery_status = confirmed
channel_adapter in ('instagram_reels', 'instagram_carousel')
payload.dry_run = false
payload.source_dispatch_plan_id = dispatch_plan_id candidato
```

Eventos `failed`, `cancelled` ou `dry_run=true` não retiram o item da fila.

A regra não cria cooldown global e não altera elegibilidade ou status do WhatsApp.

## 3. Ordem da fila

Depois de aplicar as regras de formato, mídia e não repetição Instagram, a seleção continua respeitando:

```text
order by daily_sequence
```

Não introduzir seleção manual nem fallback de formato.

Na validação real de 2026-08-23:

- `daily_sequence = 57`, item `18699616925`, foi confirmado como Reel;
- o próximo formato passou a ser Carrossel;
- com a regra de produto único, o próximo candidato natural passou a ser `daily_sequence = 58`, item `48556527725`.

Esse exemplo documenta o comportamento observado e não fixa IDs na regra de negócio.

## 4. Retry do processamento do container

A Graph API pode retornar o container inicialmente como:

```text
IN_PROGRESS
```

Nesse caso o workflow não deve falhar na primeira verificação.

O node `Pode Repetir Poll Container?` deve usar comparação numérica compatível com o IF v2 do n8n:

```text
poll_attempt < 6
```

Contrato versionado:

```json
{
  "leftValue": "={{ Number($json.poll_attempt || 0) }}",
  "rightValue": 6,
  "operator": {
    "type": "number",
    "operation": "lt"
  }
}
```

O node `Aguardar Container Instagram` permanece com:

```text
60 segundos
```

Com isso, `poll_attempt` de 1 a 5 entra no Wait e uma sexta verificação ainda não concluída segue para a falha auditável `container_not_ready_timeout`.

Não aumentar novamente essa janela sem evidência de uma nova falha real.

## 5. Registro de publicação

A publicação continua sendo considerada concluída somente quando:

- o container estiver `FINISHED`;
- `/media_publish` retornar o ID da mídia publicada;
- `offers.publication_events` registrar `delivery_status = confirmed` e `sent_at` preenchido.

A chave de auditoria existente por `channel_adapter + source_dispatch_plan_id` permanece inalterada. A regra de produto único é aplicada na seleção, não por mudança de schema nesta decisão.

## 6. Operação e implantação

Toda alteração deve ser versionada antes de chegar ao n8n da VPS.

O workflow versionado permanece:

```text
n8n/workflows/ofertas-instagram-supabase.json
```

O workflow deve permanecer `active=false` durante os testes reais manuais.

A implantação real de teste continua sendo feita explicitamente com:

```bash
./.venv/bin/python scripts/n8n/deploy_instagram_workflow_guard.py \
  --mode instagram-real-test
```

Não fazer alterações manuais não versionadas no workflow como parte deste fluxo operacional.

## 7. Critérios de aceite

- [ ] um `dispatch_plan_id` confirmado em Reel não pode ser selecionado depois para Carrossel no mesmo dia;
- [ ] um `dispatch_plan_id` confirmado em Carrossel não pode ser selecionado depois para Reel no mesmo dia;
- [ ] `failed`, `cancelled` e dry-run não removem o candidato por essa regra;
- [ ] a alternância 3 Reels + 3 Carrosséis continua baseada somente em confirmados;
- [ ] o próximo candidato continua sendo o menor `daily_sequence` elegível;
- [ ] `poll_attempt` de 1 a 5 segue para Wait;
- [ ] o Wait permanece em 60 segundos;
- [ ] a sexta verificação não pronta segue para falha auditável;
- [ ] nenhuma regra do WhatsApp é alterada;
- [ ] workflow permanece inativo após o deploy de teste.

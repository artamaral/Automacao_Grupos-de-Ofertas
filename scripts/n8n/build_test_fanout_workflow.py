from __future__ import annotations

# ruff: noqa: E501
import json
from pathlib import Path
from typing import Any

SOURCE_PATH = Path("n8n/workflows/ofertas-mvp-supabase.json")
OUTPUT_PATH = Path("n8n/workflows/ofertas-mvp-supabase-test-fanout.json")
WORKFLOW_ID = "OfertasMvpSupab1-TestFanout"
FORBIDDEN_PRODUCTION_VALUES = (
    "grupo-ofertas-feminino",
    "120363412864266334@g.us",
)


FANOUT_CONFIGURATION_CODE = """const destinations = [
  { target: 'grupo-teste-fanout', chat_id_var: 'N8N_TEST_FANOUT_GROUP_CHAT_ID', destination_kind: 'group', channel_adapter: 'whatsapp', active: true },
  { target: 'canal-teste-fanout', chat_id_var: 'N8N_TEST_FANOUT_CHANNEL_CHAT_ID', destination_kind: 'channel', channel_adapter: 'whatsapp', active: true },
];
const configured = destinations.filter((destination) => destination.active === true).map((destination) => ({
  ...destination,
  target_chat_id: String($vars[destination.chat_id_var] || '').trim(),
}));
if (configured.length !== 2) throw new Error('fanout de teste exige exatamente dois destinos ativos');
const targetNames = new Set();
for (const destination of configured) {
  if (!/^[a-z0-9][a-z0-9_-]{1,80}$/i.test(destination.target) || targetNames.has(destination.target)) throw new Error('target de teste invalido ou duplicado');
  targetNames.add(destination.target);
  if (destination.channel_adapter !== 'whatsapp') throw new Error('adapter de teste invalido');
  const expectedSuffix = destination.destination_kind === 'group' ? /@g\\.us$/ : /@newsletter$/;
  if (!expectedSuffix.test(destination.target_chat_id)) throw new Error(`chat id invalido para ${destination.destination_kind}`);
}
return [{ json: { ...$json, destinations: configured, allowed_targets: configured.map((destination) => destination.target), validation_source_preview: true, real_send_enabled: String($vars.N8N_TEST_FANOUT_REAL_SEND_ENABLED || '').toLowerCase() === 'true', send_delay_seconds_min: 45, send_delay_seconds_max: 90 } }];"""


RECURRING_CONTEXT_CODE = """const item = $json;
if (item.validation_source_preview !== true || item.real_send_enabled !== true) throw new Error('clone exige preview e habilitacao explicita de envio');
const sqlText = (value) => `'${String(value).replace(/'/g, "''")}'`;
const recurringPreviewMode = sqlText(item.recurring_preview_mode || 'current_slot');
const query = `select
  null::uuid as dispatch_plan_id,
  ready.profile, ready.marketplace, ready.stable_key, ready.item_id,
  ready.product_name, ready.offer_link, ready.image_url, ready.price,
  ready.reference_price, ready.rating, ready.sales_count, ready.primary_subniche,
  ready.commercial_score, ready.score_reasons, ready.rank_profile, ready.rank_subniche,
  ready.selection_bucket, ready.selection_reason, ready.planned_date, ready.planned_hour,
  ready.slot_sequence, ready.daily_sequence, ready.planned_at
from offers.v_daily_dispatch_ready ready
where ready.is_ready_for_dispatch
  and ready.profile = ${sqlText(item.profile)}
  and ready.marketplace = ${sqlText(item.marketplace)}
  and ready.planned_date = (now() at time zone 'America/Sao_Paulo')::date
  and (
    (coalesce(${recurringPreviewMode}, 'current_slot') = 'current_slot'
      and ready.planned_hour = extract(hour from now() at time zone 'America/Sao_Paulo')::integer)
    or
    (${recurringPreviewMode} = 'next_ready_today'
      and ready.planned_hour >= extract(hour from now() at time zone 'America/Sao_Paulo')::integer)
  )
order by ready.planned_hour, ready.slot_sequence
limit ${Number(item.limit || 1)};`;
return [{ json: { ...item, dry_run: false, dispatch_plan_id: null, ranking_query: query } }];"""


EXPAND_DESTINATIONS_CODE = """const source = $json;
const fanoutConfiguration = $('Configurar Destinos Fanout Teste').first().json;
const destinations = Array.isArray(source.destinations) && source.destinations.length > 0
  ? source.destinations
  : fanoutConfiguration.destinations;
if (!Array.isArray(destinations) || destinations.length === 0) throw new Error('destinations obrigatorio');
const fanoutRunId = `${source.run_id || source.execution_day || new Date().toISOString()}-${source.source_flow}`;
return destinations.map((destination, destinationIndex) => ({
  json: {
    ...source,
    destinations,
    allowed_targets: fanoutConfiguration.allowed_targets,
    validation_source_preview: fanoutConfiguration.validation_source_preview,
    real_send_enabled: fanoutConfiguration.real_send_enabled,
    ...destination,
    target: destination.target,
    target_chat_id: destination.target_chat_id,
    fanout_run_id: fanoutRunId,
    destination_index: destinationIndex + 1,
    destination_count: destinations.length,
  },
}));"""


PREPARE_SEND_CODE = """const item = $json;
const targetChatId = String(item.target_chat_id || '').trim();
const imageUrl = String(item.image_url || '').trim();
const imageIsValid = /^https?:\\/\\//i.test(imageUrl);
const canSend = item.real_send_enabled === true && Boolean(item.message_text && targetChatId && imageIsValid);
return {
  json: {
    ...item,
    target_allowed: true,
    waha_should_send: canSend,
    waha_chat_id: canSend ? targetChatId : null,
    waha_image_url: canSend ? imageUrl : null,
    waha_image_filename: canSend ? `oferta-${String(item.item_id || item.stable_key || 'teste').replace(/[^a-z0-9_-]/gi, '').slice(0, 80) || 'teste'}.jpg` : null,
    blocked_reason: canSend ? null : 'test_send_not_enabled_or_payload_missing',
    delivery_status: canSend ? 'pending' : 'cancelled',
    adapter_status: canSend ? 'ready_for_real_channel_node' : 'not_sent',
  },
};"""


NORMALIZE_SEND_CODE = """const original = $('PREPARE_NODE').item.json;
const response = $json || {};
const messageId = response.id?._serialized || response._data?.id?._serialized || response.id?.id || null;
const accepted = Boolean(messageId || response.fromMe === true || response._data?.fromMe === true);
return { json: { ...original, adapter_status: accepted ? 'sent_to_adapter' : 'adapter_send_failed', adapter_message_id: messageId, adapter_ack: response.ack ?? response._data?.ack ?? null, adapter_response_type: response.type || response._data?.type || null, delivery_status: accepted ? 'confirmed' : 'failed', blocked_reason: accepted ? null : 'adapter_send_failed', sent_at: accepted ? new Date().toISOString() : null } };"""


SCHEDULE_CONTEXT_CODE = """return [{ json: { profile: 'feminino', marketplace: 'shopee', limit: 1, run_id: `test-fanout-${Date.now()}`, source_flow: 'recorrente_supabase', recurring_preview_mode: 'current_slot' } }];"""


MANUAL_CONTEXT_CODE = """return [{ json: { profile: 'feminino', marketplace: 'shopee', limit: 1, run_id: `test-fanout-manual-${Date.now()}`, source_flow: 'recorrente_supabase', recurring_preview_mode: 'next_ready_today' } }];"""


def node_by_id(workflow: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in workflow["nodes"]:
        if node["id"] == node_id:
            return node
    raise KeyError(node_id)


def node_by_name(workflow: dict[str, Any], name: str) -> dict[str, Any]:
    for node in workflow["nodes"]:
        if node["name"] == name:
            return node
    raise KeyError(name)


def code_node(node_id: str, name: str, code: str, position: list[int]) -> dict[str, Any]:
    return {
        "parameters": {"jsCode": code},
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": position,
    }


def manual_trigger_node(node_id: str, name: str, position: list[int]) -> dict[str, Any]:
    return {
        "parameters": {},
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": position,
    }


def loop_node(node_id: str, name: str, position: list[int]) -> dict[str, Any]:
    return {
        "parameters": {"batchSize": 1, "options": {}},
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.splitInBatches",
        "typeVersion": 3,
        "position": position,
    }


def flow_node(node_id: str, name: str, source_flow: str, position: list[int]) -> dict[str, Any]:
    return {
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [
                    {
                        "leftValue": "={{ $json.source_flow }}",
                        "rightValue": source_flow,
                        "operator": {"type": "string", "operation": "equals"},
                    }
                ],
            },
            "options": {},
        },
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": position,
    }


def wait_node(node_id: str, name: str, position: list[int]) -> dict[str, Any]:
    return {
        "parameters": {
            "amount": "={{ Math.max(1, Number($json.send_delay_seconds_min || 45)) }}",
            "unit": "seconds",
        },
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.wait",
        "typeVersion": 1.1,
        "position": position,
    }


def set_connection(workflow: dict[str, Any], source: str, targets: list[list[str]]) -> None:
    workflow["connections"][source] = {
        "main": [
            [{"node": target, "type": "main", "index": 0} for target in branch]
            for branch in targets
        ]
    }


def remove_nodes(workflow: dict[str, Any], names: set[str]) -> None:
    workflow["nodes"] = [node for node in workflow["nodes"] if node["name"] not in names]
    for source in list(workflow["connections"]):
        if source in names:
            del workflow["connections"][source]
            continue
        for branch in workflow["connections"][source].get("main", []):
            branch[:] = [connection for connection in branch if connection["node"] not in names]


def build() -> dict[str, Any]:
    workflow = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    workflow["id"] = WORKFLOW_ID
    workflow["name"] = "ofertas-mvp-supabase-test-fanout"
    workflow["active"] = False
    workflow.pop("pinData", None)
    workflow["meta"]["description"] = (
        "Clone isolado: consulta a previa da fila e valida envio WAHA para destinos de teste."
    )
    recurring_schedule = node_by_id(workflow, "schedule-grupo-real")
    recurring_schedule["name"] = "Schedule Recorrente Fanout Teste"
    recurring_schedule["notes"] = "Executa a validacao recorrente do fan-out sem claimar a fila."
    workflow["connections"]["Schedule Recorrente Fanout Teste"] = workflow["connections"].pop(
        "Schedule Grupo Real"
    )

    remove_nodes(
        workflow,
        {
            "Montar Upsert Publication Event",
            "Registrar Resultado Supabase",
            "Montar Upsert Publication Event Estatico",
            "Registrar Resultado Supabase Estatico",
            "Montar Upsert Publication Event Pontual",
            "Registrar Resultado Supabase Pontual",
            "Preparar Arquivamento Pontual",
            "IF Deve Arquivar Pontual",
            "Buscar Pasta Enviados Drive Pontual",
            "Validar Pasta Enviados Drive Pontual",
            "IF Pasta Enviados Disponivel Pontual",
            "Buscar Pasta Dia Enviados Pontual",
            "Validar Pasta Dia Enviados Pontual",
            "IF Pasta Dia Enviados Pronta Pontual",
            "IF Criar Pasta Dia Enviados Pontual",
            "Criar Pasta Dia Enviados Pontual",
            "Normalizar Pasta Dia Criada Pontual",
            "Mover Pasta msg_XXX Pontual",
            "Normalizar Arquivamento Pontual",
            "Montar Update Arquivamento Pontual",
            "Atualizar Payload Arquivamento Pontual",
        },
    )

    node_by_name(workflow, "Set Contexto Schedule Grupo")["parameters"]["jsCode"] = (
        SCHEDULE_CONTEXT_CODE
    )
    node_by_name(workflow, "Set Contexto MVP")["parameters"]["jsCode"] = MANUAL_CONTEXT_CODE
    node_by_name(workflow, "Validar Contexto")["parameters"]["jsCode"] = RECURRING_CONTEXT_CODE
    node_by_name(workflow, "Resolver Sequencia Estatica")["parameters"]["jsCode"] = node_by_name(
        workflow, "Resolver Sequencia Estatica"
    )["parameters"]["jsCode"].replace(
        "  target: 'grupo-ofertas-feminino', target_chat_id: '120363412864266334@g.us',\n  allowed_targets: ['grupo-ofertas-feminino'], channel_adapter: 'whatsapp',\n",
        "  source_flow: 'mensagens_estaticas',\n",
    )
    node_by_name(workflow, "Resolver Sequencia Pontual")["parameters"]["jsCode"] = node_by_name(
        workflow, "Resolver Sequencia Pontual"
    )["parameters"]["jsCode"].replace(
        "  target: 'grupo-ofertas-feminino', target_chat_id: '120363412864266334@g.us',\n  allowed_targets: ['grupo-ofertas-feminino'], channel_adapter: 'whatsapp',\n",
        "  source_flow: 'mensagens_pontuais',\n",
    )

    for name in (
        "Preparar Envio WAHA",
        "Preparar Envio WAHA Estatico",
        "Preparar Envio WAHA Pontual",
    ):
        node_by_name(workflow, name)["parameters"]["jsCode"] = PREPARE_SEND_CODE
    for name, prepare_name in (
        ("Normalizar Resultado WAHA", "Preparar Envio WAHA"),
        ("Normalizar Resultado WAHA Estatico", "Preparar Envio WAHA Estatico"),
        ("Normalizar Resultado WAHA Pontual", "Preparar Envio WAHA Pontual"),
    ):
        node_by_name(workflow, name)["parameters"]["jsCode"] = NORMALIZE_SEND_CODE.replace(
            "PREPARE_NODE", prepare_name
        )

    workflow["nodes"].extend(
        [
            manual_trigger_node(
                "test-fanout-manual-static",
                "Trigger Manual Estatico Fanout Teste",
                [0, 540],
            ),
            manual_trigger_node(
                "test-fanout-manual-one-shot",
                "Trigger Manual Pontual Fanout Teste",
                [0, 960],
            ),
            code_node(
                "test-fanout-config",
                "Configurar Destinos Fanout Teste",
                FANOUT_CONFIGURATION_CODE,
                [240, -120],
            ),
            flow_node(
                "test-fanout-route-recurring",
                "IF Fluxo Recorrente Fanout",
                "recorrente_supabase",
                [460, -220],
            ),
            flow_node(
                "test-fanout-route-static",
                "IF Fluxo Estatico Fanout",
                "mensagens_estaticas",
                [460, -120],
            ),
            flow_node(
                "test-fanout-route-one-shot",
                "IF Fluxo Pontual Fanout",
                "mensagens_pontuais",
                [460, -20],
            ),
            loop_node("test-fanout-loop-recurring", "Loop Destinos Recorrente", [1540, 120]),
            code_node(
                "test-fanout-expand-static",
                "Expandir Destinos Estatico",
                EXPAND_DESTINATIONS_CODE,
                [1600, 540],
            ),
            loop_node("test-fanout-loop-static", "Loop Destinos Estatico", [1820, 540]),
            wait_node("test-fanout-wait-static", "Aguardar Intervalo WAHA Estatico", [2260, 540]),
            code_node(
                "test-fanout-expand-one-shot",
                "Expandir Destinos Pontual",
                EXPAND_DESTINATIONS_CODE,
                [1600, 960],
            ),
            loop_node("test-fanout-loop-one-shot", "Loop Destinos Pontual", [1820, 960]),
            wait_node("test-fanout-wait-one-shot", "Aguardar Intervalo WAHA Pontual", [2260, 960]),
        ]
    )

    set_connection(workflow, "Trigger Manual", [["Set Contexto MVP"]])
    set_connection(
        workflow,
        "Trigger Manual Estatico Fanout Teste",
        [["Resolver Sequencia Estatica"]],
    )
    set_connection(
        workflow,
        "Trigger Manual Pontual Fanout Teste",
        [["Resolver Sequencia Pontual"]],
    )
    set_connection(workflow, "Set Contexto MVP", [["Configurar Destinos Fanout Teste"]])
    set_connection(workflow, "Schedule Recorrente Fanout Teste", [["Set Contexto Schedule Grupo"]])
    set_connection(workflow, "Set Contexto Schedule Grupo", [["Configurar Destinos Fanout Teste"]])
    set_connection(
        workflow,
        "Configurar Destinos Fanout Teste",
        [["IF Fluxo Recorrente Fanout", "IF Fluxo Estatico Fanout", "IF Fluxo Pontual Fanout"]],
    )
    set_connection(workflow, "IF Fluxo Recorrente Fanout", [["Validar Contexto"], []])
    set_connection(workflow, "IF Fluxo Estatico Fanout", [["Buscar Pasta Raiz Drive"], []])
    set_connection(
        workflow, "IF Fluxo Pontual Fanout", [["Buscar Pasta Pendentes Drive Pontual"], []]
    )
    expand_recurring = node_by_name(workflow, "Validar Allowlist")
    expand_recurring["name"] = "Expandir Destinos Recorrente"
    expand_recurring["parameters"]["jsCode"] = EXPAND_DESTINATIONS_CODE
    expand_recurring["parameters"]["mode"] = "runOnceForAllItems"
    workflow["connections"].pop("Validar Allowlist", None)
    set_connection(workflow, "Montar Mensagens", [["Expandir Destinos Recorrente"]])
    set_connection(workflow, "Expandir Destinos Recorrente", [["Loop Destinos Recorrente"]])
    set_connection(
        workflow,
        "Loop Destinos Recorrente",
        [["Loop Ofertas"], ["Simular Envio MVP"]],
    )
    set_connection(
        workflow, "IF Pode Enviar WAHA", [["Aguardar Intervalo WAHA"], ["Loop Destinos Recorrente"]]
    )
    set_connection(workflow, "Normalizar Resultado WAHA", [["Loop Destinos Recorrente"]])

    set_connection(workflow, "Resolver Sequencia Estatica", [["Configurar Destinos Fanout Teste"]])
    set_connection(workflow, "IF Conteudo Estatico Valido", [["Expandir Destinos Estatico"], []])
    set_connection(workflow, "Expandir Destinos Estatico", [["Loop Destinos Estatico"]])
    set_connection(workflow, "Loop Destinos Estatico", [[], ["Preparar Envio WAHA Estatico"]])
    set_connection(
        workflow,
        "IF Pode Enviar WAHA Estatico",
        [["Aguardar Intervalo WAHA Estatico"], ["Loop Destinos Estatico"]],
    )
    set_connection(
        workflow, "Aguardar Intervalo WAHA Estatico", [["Enviar WhatsApp WAHA Estatico"]]
    )
    set_connection(workflow, "Normalizar Resultado WAHA Estatico", [["Loop Destinos Estatico"]])

    set_connection(workflow, "Resolver Sequencia Pontual", [["Configurar Destinos Fanout Teste"]])
    set_connection(workflow, "IF Conteudo Pontual Valido", [["Expandir Destinos Pontual"], []])
    set_connection(workflow, "Expandir Destinos Pontual", [["Loop Destinos Pontual"]])
    set_connection(workflow, "Loop Destinos Pontual", [[], ["Preparar Envio WAHA Pontual"]])
    set_connection(
        workflow,
        "IF Pode Enviar WAHA Pontual",
        [["Aguardar Intervalo WAHA Pontual"], ["Loop Destinos Pontual"]],
    )
    set_connection(workflow, "Aguardar Intervalo WAHA Pontual", [["Enviar WhatsApp WAHA Pontual"]])
    set_connection(workflow, "Normalizar Resultado WAHA Pontual", [["Loop Destinos Pontual"]])

    for name in (
        "Expandir Destinos Estatico",
        "Expandir Destinos Pontual",
    ):
        node_by_name(workflow, name)["parameters"]["mode"] = "runOnceForAllItems"

    serialized = json.dumps(workflow, ensure_ascii=False)
    for forbidden in FORBIDDEN_PRODUCTION_VALUES:
        if forbidden in serialized:
            raise ValueError(f"forbidden production value remains: {forbidden}")
    if "offers.publication_events" in serialized:
        raise ValueError("clone must not contain publication_events")
    return workflow


def main() -> int:
    OUTPUT_PATH.write_text(
        json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

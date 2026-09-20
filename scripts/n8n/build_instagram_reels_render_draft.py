from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Embedded n8n expressions intentionally contain long JSON/JavaScript lines.
# ruff: noqa: E501


SOURCE = Path("n8n/workflows/ofertas-instagram-supabase.json")
OUTPUT = Path("n8n/workflows/ofertas-instagram-reels-render-draft.json")
DRIVE_FOLDER_ID = "1Fk_D3IXQ_qMZikJ5UBwIV2xTDa0Rwj2W"
RENDER_CREDENTIAL = {"id": "reelsRendererBearer1", "name": "Reels Renderer Bearer"}
DRIVE_CREDENTIAL = {"id": "mpDU88mNaqYR5jzz", "name": "Google Drive account"}


def node(name: str, node_type: str, node_id: str, parameters: dict[str, Any], position: list[int]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "parameters": parameters,
        "id": node_id,
        "name": name,
        "type": node_type,
        "typeVersion": 2,
        "position": position,
    }
    return result


def code_node(name: str, node_id: str, code: str, position: list[int]) -> dict[str, Any]:
    return node(
        name,
        "n8n-nodes-base.code",
        node_id,
        {"jsCode": code},
        position,
    )


def add_nodes(workflow: dict[str, Any]) -> None:
    workflow["nodes"] = [
        n
        for n in workflow["nodes"]
        if n["name"] not in {
            "Selecionar Template Reels",
            "Buscar Template ASS Reels",
            "Escolher Template ASS Reels",
            "Baixar Template ASS Reels",
            "Montar Payload Render Reels",
            "Criar Job Render Reels",
            "Normalizar Job Render Reels",
            "Job Render Aceito?",
            "Checar Status Render Reels",
            "Restaurar Contexto Render Reels",
            "Render Pronto?",
            "Pode Repetir Render Reels?",
            "Aguardar Render Reels",
            "Falhar Render Reels",
        }
    ]
    workflow["nodes"].extend(
        [
            code_node(
                "Selecionar Template Reels",
                "selecionar-template-reels",
                """const item = $json;
const requested = Number($('Trigger Manual').first().json.template_id_override);
const template_id = Number.isInteger(requested) && requested >= 1 && requested <= 10
  ? requested
  : Math.floor(Math.random() * 10) + 1;
return [{ json: { ...item, template_id, template_folder_id: 'DRIVE_FOLDER_ID' } }];""".replace(
                    "DRIVE_FOLDER_ID", DRIVE_FOLDER_ID
                ),
                [1180, 460],
            ),
            node(
                "Buscar Template ASS Reels",
                "n8n-nodes-base.googleDrive",
                "buscar-template-ass-reels",
                {
                    "authentication": "oAuth2",
                    "resource": "fileFolder",
                    "operation": "search",
                    "searchMethod": "query",
                    "returnAll": True,
                    "queryString": "name contains 'template_' and trashed = false",
                    "filter": {
                        "folderId": {
                            "__rl": True,
                            "value": "={{ $('Selecionar Template Reels').first().json.template_folder_id }}",
                            "mode": "id",
                        },
                        "whatToSearch": "files",
                        "includeTrashed": False,
                    },
                    "options": {"fields": ["id", "name", "mimeType", "webViewLink"]},
                },
                [1400, 460],
            ) | {"typeVersion": 3, "credentials": {"googleDriveOAuth2Api": DRIVE_CREDENTIAL}},
            code_node(
                "Escolher Template ASS Reels",
                "escolher-template-ass-reels",
                """const context = $('Selecionar Template Reels').first().json;
const expected = `template_${String(context.template_id).padStart(2, '0')}.ass`;
const matches = $input.all().filter((entry) => String(entry.json.name || '') === expected);
if (matches.length !== 1) throw new Error(`template ASS ausente ou ambiguo: ${expected}`);
return [{ json: { ...context, ass_file_id: matches[0].json.id, ass_file_name: expected } }];""",
                [1620, 460],
            ),
            node(
                "Baixar Template ASS Reels",
                "n8n-nodes-base.googleDrive",
                "baixar-template-ass-reels",
                {
                    "authentication": "oAuth2",
                    "resource": "file",
                    "operation": "download",
                    "fileId": {
                        "__rl": True,
                        "value": "={{ $json.ass_file_id }}",
                        "mode": "id",
                    },
                    "options": {
                        "binaryPropertyName": "ass_template",
                        "fileName": "={{ $json.ass_file_name }}",
                    },
                },
                [1840, 460],
            ) | {"typeVersion": 3, "credentials": {"googleDriveOAuth2Api": DRIVE_CREDENTIAL}},
            code_node(
                "Montar Payload Render Reels",
                "montar-payload-render-reels",
                """const context = $('Escolher Template ASS Reels').first().json;
const binary = await this.helpers.getBinaryDataBuffer(0, 'ass_template');
if (!binary?.length) throw new Error('ASS template nao retornado pelo Google Drive');
const safe = (value) => String(value || '').replace(/[^A-Za-z0-9_-]/g, '-').slice(0, 40);
const job_id = `reels-${safe(context.dispatch_plan_id)}-${safe(context.item_id)}-t${context.template_id}`;
return [{ json: {
  ...context,
  job_id,
  ass_template_base64: binary.toString('base64'),
  ass_asset_version: context.ass_file_id,
  render_status: 'queued',
  render_attempts: 0,
} }];""",
                [2060, 460],
            ),
            node(
                "Criar Job Render Reels",
                "n8n-nodes-base.httpRequest",
                "criar-job-render-reels",
                {
                    "method": "POST",
                    "url": "http://reels-renderer:8080/v1/render/jobs",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ job_id: $json.job_id, item_id: String($json.item_id), planned_date: $json.planned_date, source_dispatch_plan_id: String($json.dispatch_plan_id), video_url: $json.video_url, price: String($json.price), template_id: $json.template_id, ass_template_base64: $json.ass_template_base64 }) }}",
                    "options": {
                        "response": {"response": {"neverError": True, "responseFormat": "json"}},
                        "timeout": 15000,
                    },
                },
                [2280, 460],
            ) | {"typeVersion": 4.2, "credentials": {"httpHeaderAuth": RENDER_CREDENTIAL}, "continueOnFail": True},
            code_node(
                "Normalizar Job Render Reels",
                "normalizar-job-render-reels",
                """const response = $json || {};
const original = $('Montar Payload Render Reels').first().json;
const failed = Boolean(response.error || Number(response.statusCode || 0) >= 400 || !String(response.job_id || '').trim());
return [{ json: { ...original, ...response, job_id: response.job_id || original.job_id, render_status: failed ? 'failed_fallback_original' : (response.render_status || response.status || 'queued'), render_error_code: failed ? 'RENDER_SUBMIT_FAILED' : '', render_error_log: failed ? String(response.error || response.message || '').slice(0, 2000) : '', poll_attempt: 0 } }];""",
                [2500, 460],
            ),
            node(
                "Job Render Aceito?",
                "n8n-nodes-base.if",
                "job-render-aceito",
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [{"id": "job-accepted", "leftValue": "={{ $json.render_status }}", "rightValue": "failed_fallback_original", "operator": {"type": "string", "operation": "notEquals"}}],
                        "combinator": "and",
                    }
                },
                [2720, 560],
            ),
            node(
                "Checar Status Render Reels",
                "n8n-nodes-base.httpRequest",
                "checar-status-render-reels",
                {
                    "method": "GET",
                    "url": "={{ 'http://reels-renderer:8080/v1/render/jobs/' + $json.job_id }}",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                    "options": {
                        "response": {"response": {"neverError": True, "responseFormat": "json"}},
                        "timeout": 10000,
                    },
                },
                [2720, 460],
            ) | {"typeVersion": 4.2, "credentials": {"httpHeaderAuth": RENDER_CREDENTIAL}, "continueOnFail": True},
            code_node(
                "Restaurar Contexto Render Reels",
                "restaurar-contexto-render-reels",
                """const response = $json;
const original = $('Normalizar Job Render Reels').first().json;
 const errors = Array.isArray(response.errors) ? response.errors : [];
 const accountId = String(original.instagram_business_account_id || $('Montar Copy Instagram').first().json.instagram_business_account_id || $('Trigger Manual').first().json.instagram_business_account_id || '').trim();
 if (!accountId) throw new Error('instagram_business_account_id ausente ao restaurar contexto do render');
 return [{ json: {
   ...original,
   ...response,
   instagram_business_account_id: accountId,
  job_id: response.job_id || original.job_id,
  render_status: response.render_status || response.status || 'running',
  render_attempts: Number(response.attempts || original.render_attempts || 0),
  poll_attempt: Number(original.poll_attempt || 0) + 1,
  render_error_code: errors.at(-1)?.code || '',
  render_error_log: errors.map((error) => error.message || '').join(' | ').slice(0, 2000),
  published_video_url: response.artifact_url || '',
} }];""",
                [2940, 460],
            ),
            node(
                "Render Pronto?",
                "n8n-nodes-base.if",
                "render-pronto",
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [{"id": "render-succeeded", "leftValue": "={{ $json.render_status }}", "rightValue": "succeeded", "operator": {"type": "string", "operation": "equals"}}],
                        "combinator": "and",
                    }
                },
                [3160, 460],
            ),
            node(
                "Pode Repetir Render Reels?",
                "n8n-nodes-base.if",
                "pode-repetir-render-reels",
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [{"id": "render-poll-limit", "leftValue": "={{ Number($json.poll_attempt || 0) }}", "rightValue": 30, "operator": {"type": "number", "operation": "lt"}}],
                        "combinator": "and",
                    }
                },
                [3380, 560],
            ),
            node(
                "Aguardar Render Reels",
                "n8n-nodes-base.wait",
                "aguardar-render-reels",
                {"resume": "timeInterval", "amount": 10, "unit": "seconds"},
                [3600, 460],
            ),
            code_node(
                "Falhar Render Reels",
                "falhar-render-reels",
                """return [{ json: {
  ...$json,
  render_status: 'failed_fallback_original',
  overlay_applied: false,
  published_video_source: 'shopee_original',
  published_video_url: '',
} }];""",
                [3600, 660],
            ),
        ]
    )


def update_connections(workflow: dict[str, Any]) -> None:
    connections = workflow["connections"]
    connections["Montar Copy Instagram"] = {"main": [[{"node": "Revalidar Midia", "type": "main", "index": 0}]]}
    connections["Revalidar Midia"] = {"main": [[{"node": "Selecionar Template Reels", "type": "main", "index": 0}]]}
    one_way = {
        "Selecionar Template Reels": "Buscar Template ASS Reels",
        "Buscar Template ASS Reels": "Escolher Template ASS Reels",
        "Escolher Template ASS Reels": "Baixar Template ASS Reels",
        "Baixar Template ASS Reels": "Montar Payload Render Reels",
        "Montar Payload Render Reels": "Criar Job Render Reels",
        "Criar Job Render Reels": "Normalizar Job Render Reels",
        "Normalizar Job Render Reels": "Job Render Aceito?",
        "Checar Status Render Reels": "Restaurar Contexto Render Reels",
        "Restaurar Contexto Render Reels": "Render Pronto?",
        "Aguardar Render Reels": "Checar Status Render Reels",
        "Falhar Render Reels": "Dry Run Instagram?",
    }
    for source, target in one_way.items():
        connections[source] = {"main": [[{"node": target, "type": "main", "index": 0}]]}
    connections["Job Render Aceito?"] = {
        "main": [
            [{"node": "Checar Status Render Reels", "type": "main", "index": 0}],
            [{"node": "Falhar Render Reels", "type": "main", "index": 0}],
        ]
    }
    connections["Render Pronto?"] = {
        "main": [
            [{"node": "Dry Run Instagram?", "type": "main", "index": 0}],
            [{"node": "Pode Repetir Render Reels?", "type": "main", "index": 0}],
        ]
    }
    connections["Dry Run Instagram?"] = {
        "main": [
            [{"node": "Registrar Resultado Supabase", "type": "main", "index": 0}],
            [{"node": "Criar Container Reels", "type": "main", "index": 0}],
        ]
    }
    connections["Pode Repetir Render Reels?"] = {
        "main": [
            [{"node": "Aguardar Render Reels", "type": "main", "index": 0}],
            [{"node": "Falhar Render Reels", "type": "main", "index": 0}],
        ]
    }


def update_reels_publish_node(workflow: dict[str, Any]) -> None:
    publish = next(node for node in workflow["nodes"] if node["name"] == "Criar Container Reels")
    for parameter in publish["parameters"]["bodyParameters"]["parameters"]:
        if parameter["name"] == "video_url":
            parameter["value"] = "={{ $json.published_video_url || $json.video_url }}"


def update_result_query(workflow: dict[str, Any]) -> None:
    register = next(node for node in workflow["nodes"] if node["name"] == "Registrar Resultado Supabase")
    query = register["parameters"]["query"]
    marker = "    'published_media_id', '{{ $json.instagram_media_id || \"\" }}'\n"
    replacement = marker[:-1] + ",\n    'template_id', coalesce({{ $json.template_id || 'null' }}, null),\n    'ass_asset_version', '{{ $json.ass_asset_version || \"\" }}',\n    'render_status', '{{ $json.render_status || \"not_attempted\" }}',\n    'render_attempts', coalesce({{ $json.render_attempts || 0 }}, 0),\n    'render_error_code', '{{ $json.render_error_code || \"\" }}',\n    'render_error_log', '{{ $json.render_error_log || \"\" }}',\n    'overlay_applied', coalesce({{ $json.overlay_applied ? 'true' : 'false' }}, false),\n    'published_video_source', '{{ $json.published_video_source || \"shopee_original\" }}'\n"
    if marker not in query:
        raise ValueError("publication query marker not found")
    register["parameters"]["query"] = query.replace(marker, replacement)


def build() -> dict[str, Any]:
    workflow = json.loads(SOURCE.read_text(encoding="utf-8"))
    workflow["id"] = "OfertasInstagramReelsRenderDraft"
    workflow["name"] = "ofertas-instagram-reels-render-draft"
    workflow["active"] = False
    workflow.setdefault("meta", {})["description"] = (
        "Draft inativo: renderer VPS assíncrono para Reels; não substitui o workflow produtivo."
    )
    add_nodes(workflow)
    update_connections(workflow)
    update_reels_publish_node(workflow)
    update_result_query(workflow)
    return workflow


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: workflow draft gerado em {OUTPUT}")

# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ops_common import (
    ComposeConfig,
    N8nOpsError,
    compact_json,
    compose_psql_command,
    dollar_quote,
    sql_literal,
)

DEFAULT_WORKFLOW_JSON = Path("n8n/workflows/ofertas-instagram-interactions-supabase.json")
DEFAULT_WORKFLOW_ID = "OfertasInstagramInteractionsSupab1"
DEFAULT_COMPOSE_ENV = Path("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE_FILE = Path("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
DRIVE_FOLDER_ID = "1om8GcfC4s4UMBU9t7ujmxXawdoYIWUQy"
EXPECTED_HTTP_HEADER_CREDENTIAL = {"id": "instagramGraphHdrAuth1", "name": "Instagram Graph Bearer"}


class InstagramInteractionsWorkflowGuardError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and deploy the isolated Instagram interactions workflow.")
    parser.add_argument("--workflow-json", type=Path, default=DEFAULT_WORKFLOW_JSON)
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--compose-env", type=Path, default=DEFAULT_COMPOSE_ENV)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mode", choices=("safe", "preserve-pindata"), default="safe")
    return parser.parse_args(argv)


def load_workflow(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InstagramInteractionsWorkflowGuardError(f"workflow JSON not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InstagramInteractionsWorkflowGuardError(f"invalid workflow JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise InstagramInteractionsWorkflowGuardError("workflow JSON must be an object")
    return value


def node_by_name(workflow: dict[str, Any], name: str) -> dict[str, Any] | None:
    for node in workflow.get("nodes", []):
        if isinstance(node, dict) and node.get("name") == name:
            return node
    return None


def workflow_text(workflow: dict[str, Any]) -> str:
    return json.dumps(workflow, ensure_ascii=False, sort_keys=True)


def validate_versioned_workflow(workflow: dict[str, Any], workflow_id: str) -> None:
    errors: list[str] = []
    if workflow.get("id") != workflow_id:
        errors.append("workflow id mismatch")
    if workflow.get("active") is not False:
        errors.append("workflow active must be false")
    if workflow.get("settings", {}).get("timezone") != "America/Sao_Paulo":
        errors.append("workflow timezone must be America/Sao_Paulo")
    if not isinstance(workflow.get("connections"), dict):
        errors.append("workflow connections must be an object")

    required_nodes = (
        "Webhook Meta GET", "Validar Challenge Meta", "Responder Challenge Meta", "Webhook Meta POST",
        "Normalizar Evento Instagram", "Roteador Comentario DM Outros", "Roteador DM ou Outros", "Ignorar Comentario Proprio",
        "Registrar Comentario Recebido", "Baixar instagram_comment_keywords.txt", "Match Keywords CONTAINS",
        "Resolver Publication Event", "Baixar instagram_comment_dm_intro.txt",
        "Baixar instagram_comment_public_reply.txt", "Responder Comentario Publicamente",
        "Enviar Private Reply Comentario", "Registrar Resultado Comentario", "Ignorar DM Propria",
        "Registrar DM Recebida", "Consultar Cooldown DM", "Baixar instagram_dm_default_reply.txt",
        "Enviar Resposta DM", "Registrar Resultado DM",
    )
    for name in required_nodes:
        if node_by_name(workflow, name) is None:
            errors.append(f"missing node: {name}")

    webhook_ids: set[str] = set()
    for name in ("Webhook Meta GET", "Webhook Meta POST"):
        node = node_by_name(workflow, name)
        webhook_id = node.get("webhookId") if isinstance(node, dict) else None
        if not isinstance(webhook_id, str) or not webhook_id:
            errors.append(f"missing webhookId: {name}")
        elif webhook_id in webhook_ids:
            errors.append(f"duplicate webhookId: {webhook_id}")
        else:
            webhook_ids.add(webhook_id)

    for node in workflow.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if node.get("type") == "n8n-nodes-base.postgres":
            credential = node.get("credentials", {}).get("postgres")
            if not isinstance(credential, dict) or not credential.get("id") or not credential.get("name"):
                errors.append(f"missing postgres credentials: {node.get('name')}")
        if node.get("type") == "n8n-nodes-base.googleDrive":
            if node.get("typeVersion") != 3 or node.get("parameters", {}).get("authentication") != "oAuth2":
                errors.append(f"invalid Google Drive node: {node.get('name')}")
            if node.get("credentials"):
                errors.append(f"Google Drive credential must not be versioned: {node.get('name')}")
        if node.get("type") == "n8n-nodes-base.httpRequest":
            credential = node.get("credentials", {}).get("httpHeaderAuth")
            if credential != EXPECTED_HTTP_HEADER_CREDENTIAL:
                errors.append(f"missing httpHeaderAuth credentials: {node.get('name')}")

    text = workflow_text(workflow)
    required_text = (
        "hub.verify_token", "hub.challenge", "$vars.INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "comment_id", "message_id", "payload ->> 'published_media_id'",
        "instagram_comment_dm_intro.txt", "instagram_comment_public_reply.txt", "instagram_dm_default_reply.txt",
        "instagram_comment_keywords.txt", DRIVE_FOLDER_ID, "includes(keyword)", "15 minutes",
        "/replies", "/messages", "recipient: { comment_id", "recipient: { id:", "graph.facebook.com/v26.0",
        "processing_status", "failure_stage", "error_code", "error_detail", "raw_payload",
    )
    for value in required_text:
        if value not in text:
            errors.append(f"missing workflow contract text: {value}")
    forbidden_text = ("$env.INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "WAHA", "/api/send", "media_publish", "offer_media_assets", "daily_dispatch_plan",
                          "v_offer_ranking_current", "process.env", "agent", "llm", "redis", "message buffer", "graph.instagram.com")
    lower_text = text.lower()
    for value in forbidden_text:
        if value.lower() in lower_text:
            errors.append(f"forbidden text found: {value}")
    for url in _http_urls(workflow):
        if "graph.facebook.com/v26.0" not in url:
            errors.append(f"forbidden HTTP endpoint: {url}")
    if errors:
        raise InstagramInteractionsWorkflowGuardError("; ".join(errors))


def _http_urls(workflow: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for node in workflow.get("nodes", []):
        if isinstance(node, dict) and node.get("type") == "n8n-nodes-base.httpRequest":
            urls.append(str(node.get("parameters", {}).get("url", "")))
    return urls


def build_update_sql(workflow: dict[str, Any], workflow_id: str) -> str:
    for field in ("nodes", "connections"):
        if field not in workflow:
            raise InstagramInteractionsWorkflowGuardError(f"workflow missing required field: {field}")
    return (
        "with existing as (select nodes::jsonb as nodes from workflow_entity where id = "
        f"{sql_literal(workflow_id)}), input_nodes as (select {dollar_quote(compact_json(workflow['nodes']))}::jsonb as nodes), merged_nodes as (select coalesce(jsonb_agg(case when node->>'type' = 'n8n-nodes-base.googleDrive' then case when existing_node.credentials is not null then jsonb_set(node, '{{credentials}}', existing_node.credentials) else node end else node end), '[]'::jsonb) as nodes from input_nodes cross join lateral jsonb_array_elements(input_nodes.nodes) node left join lateral (select existing_node->'credentials' as credentials from existing cross join lateral jsonb_array_elements(existing.nodes) existing_node where existing_node->>'name' = node->>'name' and existing_node->>'type' = 'n8n-nodes-base.googleDrive' and coalesce(existing_node->'credentials', '{{}}'::jsonb) <> '{{}}'::jsonb limit 1) existing_node on true), upserted as (insert into workflow_entity (id, name, active, nodes, connections, settings, \"pinData\", \"versionId\", \"versionCounter\", \"nodeGroups\") values ("
        f"{sql_literal(workflow_id)}, {sql_literal(str(workflow.get('name') or workflow_id))}, false, "
        f"(select nodes::json from merged_nodes), {dollar_quote(compact_json(workflow['connections']))}::json, "
        f"{dollar_quote(compact_json(workflow.get('settings', {})))}::json, '{{}}'::json, gen_random_uuid()::text, 1, '[]'::json) "
        "on conflict (id) do update set nodes = excluded.nodes, connections = excluded.connections, settings = excluded.settings, active = false, \"versionId\" = gen_random_uuid()::text, \"versionCounter\" = coalesce(workflow_entity.\"versionCounter\", 0) + 1, \"updatedAt\" = now() returning id, \"versionId\", \"updatedAt\", nodes, connections, name), project as (select \"projectId\" from shared_workflow order by \"updatedAt\" desc limit 1), shared as (insert into shared_workflow (\"workflowId\", \"projectId\", role) select upserted.id, project.\"projectId\", 'workflow:owner' from upserted cross join project on conflict (\"workflowId\", \"projectId\") do nothing) "
        "insert into workflow_history (\"versionId\", \"workflowId\", authors, \"createdAt\", \"updatedAt\", nodes, connections, name, autosaved, description, \"nodeGroups\") select \"versionId\", id, 'system', \"updatedAt\", \"updatedAt\", nodes, connections, name, false, null, '[]'::json from upserted;"
    )


def run(args: argparse.Namespace) -> int:
    workflow = load_workflow(args.workflow_json)
    validate_versioned_workflow(workflow, args.workflow_id)
    sql = build_update_sql(workflow, args.workflow_id)
    if args.dry_run:
        print("INFO | dry_run=true; no changes applied")
        print("INFO | instagram interactions workflow=ok")
        print("INFO | active=false")
        print(f"INFO | sql_bytes={len(sql.encode('utf-8'))}")
        return 0
    completed = subprocess.run(compose_psql_command(ComposeConfig(args.compose_env, args.compose_file)), input=sql, text=True, encoding="utf-8", capture_output=True, check=False)
    if completed.returncode:
        raise InstagramInteractionsWorkflowGuardError(f"failed to update n8n workflow: {completed.stderr.strip()}")
    print("INFO | workflow deployed as inactive draft")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except (InstagramInteractionsWorkflowGuardError, N8nOpsError, json.JSONDecodeError) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

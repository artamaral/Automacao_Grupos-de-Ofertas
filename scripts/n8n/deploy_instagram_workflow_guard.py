from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
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

DEFAULT_WORKFLOW_JSON = Path("n8n/workflows/ofertas-instagram-supabase.json")
DEFAULT_COMPOSE_ENV = Path("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE_FILE = Path("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
DEFAULT_WORKFLOW_ID = "OfertasInstagramSupab1"
EXPECTED_WORKFLOW_TIMEZONE = "America/Sao_Paulo"
EXPECTED_TARGET = "oferta.femininas"


class InstagramWorkflowGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeployConfig:
    workflow_json: Path
    workflow_id: str
    compose_env: Path
    compose_file: Path
    pin_data: dict[str, Any] | None
    dry_run: bool


def build_pin_data(*, dry_run: bool, run_id: str) -> dict[str, Any]:
    return {
        "Trigger Manual": [
            {
                "json": {
                    "dry_run": dry_run,
                    "profile": "feminino",
                    "marketplace": "shopee",
                    "target": EXPECTED_TARGET,
                    "allowed_targets_csv": EXPECTED_TARGET,
                    "limit": 1,
                    "run_id": run_id,
                    "instagram_account_email": "grupodeofertas.mktdigital.fem@gmail.com",
                    "instagram_username": EXPECTED_TARGET,
                }
            }
        ]
    }


SAFE_PINDATA = build_pin_data(dry_run=True, run_id="instagram-safe-dry-run")
REAL_TEST_PINDATA = build_pin_data(dry_run=False, run_id="instagram-real-test")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and deploy the guarded Instagram n8n workflow JSON."
    )
    parser.add_argument("--workflow-json", type=Path, default=DEFAULT_WORKFLOW_JSON)
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--compose-env", type=Path, default=DEFAULT_COMPOSE_ENV)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("safe", "instagram-real-test", "preserve-pindata"),
        default="safe",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> DeployConfig:
    pin_data = {
        "safe": SAFE_PINDATA,
        "instagram-real-test": REAL_TEST_PINDATA,
        "preserve-pindata": None,
    }[args.mode]
    return DeployConfig(
        workflow_json=args.workflow_json,
        workflow_id=args.workflow_id,
        compose_env=args.compose_env,
        compose_file=args.compose_file,
        pin_data=pin_data,
        dry_run=args.dry_run,
    )


def load_workflow(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InstagramWorkflowGuardError(f"workflow JSON not found: {path}")
    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InstagramWorkflowGuardError(f"invalid workflow JSON: {path}: {exc}") from exc
    if not isinstance(workflow, dict):
        raise InstagramWorkflowGuardError("workflow JSON must be an object")
    return workflow


def workflow_text(workflow: dict[str, Any]) -> str:
    return json.dumps(workflow, ensure_ascii=False, sort_keys=True)


def node_by_name(workflow: dict[str, Any], name: str) -> dict[str, Any] | None:
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        return None
    for node in nodes:
        if isinstance(node, dict) and node.get("name") == name:
            return node
    return None


def validate_versioned_workflow(workflow: dict[str, Any], workflow_id: str) -> None:
    errors: list[str] = []
    if workflow.get("id") != workflow_id:
        errors.append(f"workflow id mismatch: expected {workflow_id}, got {workflow.get('id')}")
    if workflow.get("active") is not False:
        errors.append("workflow active must be false")
    if not isinstance(workflow.get("nodes"), list):
        errors.append("workflow nodes must be a list")
    if not isinstance(workflow.get("connections"), dict):
        errors.append("workflow connections must be an object")
    if workflow.get("settings", {}).get("timezone") != EXPECTED_WORKFLOW_TIMEZONE:
        errors.append(f"workflow timezone must be {EXPECTED_WORKFLOW_TIMEZONE}")

    for node_name in (
        "Trigger Manual",
        "Validar Contexto Instagram",
        "Claim Item Instagram",
        "Revalidar Midia",
        "Roteador Formato",
        "Criar Container Reels",
        "Criar Filhos Carrossel",
        "Criar Container Pai Carrossel",
        "Checar Status Container",
        "Publicar Container",
        "Marcar Midia Expirada",
        "Registrar Resultado Supabase",
    ):
        if node_by_name(workflow, node_name) is None:
            errors.append(f"missing node: {node_name}")

    text = workflow_text(workflow)
    for required_text in (
        "offers.v_instagram_dispatch_ready",
        "offers.daily_dispatch_plan",
        "for update of plan skip locked",
        "ready.instagram_format",
        "offers.offer_media_assets",
        "status = 'stale'",
        "media_revalidation_failed",
        "insert into offers.publication_events",
        "channel_adapter",
        "instagram_reels",
        "instagram_carousel",
        "delivery_status",
        "INSTAGRAM_ACCESS_TOKEN",
        "media_type=REELS",
        "media_type=CAROUSEL",
        "is_carousel_item=true",
        "/media_publish",
    ):
        if required_text not in text:
            errors.append(f"missing workflow contract text: {required_text}")
    for forbidden_text in (
        "/api/sendImage",
        "/api/sendText",
        "WAHA",
        "WhatsApp",
        "target_chat_id",
        "120363412864266334",
    ):
        if forbidden_text in text:
            errors.append(f"forbidden WhatsApp/WAHA text found: {forbidden_text}")

    if errors:
        raise InstagramWorkflowGuardError("; ".join(errors))


def validate_pin_data(pin_data: dict[str, Any] | None) -> None:
    if pin_data is None:
        return
    try:
        payload = pin_data["Trigger Manual"][0]["json"]
    except (KeyError, IndexError, TypeError) as exc:
        raise InstagramWorkflowGuardError("pinData must contain Trigger Manual[0].json") from exc
    if not isinstance(payload.get("dry_run"), bool):
        raise InstagramWorkflowGuardError("pinData dry_run must be boolean")
    if payload.get("target") != EXPECTED_TARGET:
        raise InstagramWorkflowGuardError(f"pinData target must be {EXPECTED_TARGET}")
    allowed_targets = str(payload.get("allowed_targets_csv", "")).split(",")
    if EXPECTED_TARGET not in {target.strip() for target in allowed_targets}:
        raise InstagramWorkflowGuardError("pinData target must be allowlisted")


def build_update_sql(
    workflow: dict[str, Any],
    workflow_id: str,
    pin_data: dict[str, Any] | None,
) -> str:
    required_fields = ("nodes", "connections")
    missing = [field for field in required_fields if field not in workflow]
    if missing:
        raise InstagramWorkflowGuardError(f"workflow missing required fields: {missing}")
    assignments = [
        f"nodes = {dollar_quote(compact_json(workflow['nodes']))}::json",
        f"connections = {dollar_quote(compact_json(workflow['connections']))}::json",
        f"settings = {dollar_quote(compact_json(workflow.get('settings', {})))}::json",
        "active = false",
        '"versionId" = gen_random_uuid()::text',
        '"versionCounter" = coalesce(workflow_entity."versionCounter", 0) + 1',
        '"updatedAt" = now()',
    ]
    if pin_data is not None:
        assignments.insert(3, f'"pinData" = {dollar_quote(compact_json(pin_data))}::json')
    insert_columns = [
        "id",
        "name",
        "active",
        "nodes",
        "connections",
        "settings",
        '"pinData"',
        '"versionId"',
        '"versionCounter"',
        '"nodeGroups"',
    ]
    insert_values = [
        sql_literal(workflow_id),
        sql_literal(str(workflow.get("name") or workflow_id)),
        "false",
        f"{dollar_quote(compact_json(workflow['nodes']))}::json",
        f"{dollar_quote(compact_json(workflow['connections']))}::json",
        f"{dollar_quote(compact_json(workflow.get('settings', {})))}::json",
        (
            f"{dollar_quote(compact_json(pin_data))}::json"
            if pin_data is not None
            else f"{dollar_quote(compact_json(workflow.get('pinData', {})))}::json"
        ),
        "gen_random_uuid()::text",
        "1",
        "'[]'::json",
    ]
    return (
        "with upserted_workflow as (\n"
        "  insert into workflow_entity (\n"
        f"    {', '.join(insert_columns)}\n"
        "  )\n"
        f"  values ({', '.join(insert_values)})\n"
        "  on conflict (id)\n"
        "  do update\n"
        f"  set {', '.join(assignments)}\n"
        '  returning id, "versionId", name, nodes, connections, "updatedAt"\n'
        "), shared_project as (\n"
        '  select shared."projectId"\n'
        "  from shared_workflow shared\n"
        "  order by shared.\"updatedAt\" desc\n"
        "  limit 1\n"
        "), inserted_share as (\n"
        '  insert into shared_workflow ("workflowId", "projectId", role)\n'
        '  select upserted.id, shared_project."projectId", \'workflow:owner\'\n'
        "  from upserted_workflow upserted\n"
        "  cross join shared_project\n"
        '  on conflict ("workflowId", "projectId") do nothing\n'
        '  returning "workflowId"\n'
        ")\n"
        "insert into workflow_history (\n"
        '  "versionId", "workflowId", authors, "createdAt", "updatedAt",\n'
        '  nodes, connections, name, autosaved, description, "nodeGroups"\n'
        ")\n"
        "select\n"
        '  upserted."versionId", upserted.id,\n'
        "  coalesce((select history.authors from workflow_history history "
        'where history."workflowId" = upserted.id order by history."createdAt" desc limit 1), '
        "'system'),\n"
        '  upserted."updatedAt", upserted."updatedAt", upserted.nodes,\n'
        "  upserted.connections, upserted.name, false, null, '[]'::json\n"
        "from upserted_workflow upserted;"
    )


def build_status_query(workflow_id: str) -> str:
    return (
        "select json_build_object("
        "'id', id, "
        "'active', active, "
        "'versionId', \"versionId\", "
        "'versionCounter', \"versionCounter\", "
        "'updatedAt', \"updatedAt\", "
        "'has_instagram_ready_view', "
        "position('offers.v_instagram_dispatch_ready' in nodes::text) > 0, "
        "'has_media_publish', position('/media_publish' in nodes::text) > 0, "
        "'has_waha', position('WAHA' in nodes::text) > 0, "
        "'history_exists', exists (select 1 from workflow_history history "
        'where history."workflowId" = workflow_entity.id '
        'and history."versionId" = workflow_entity."versionId"'
        "), "
        "'pinData', \"pinData\""
        ")::text "
        "from workflow_entity "
        f"where id = {sql_literal(workflow_id)};"
    )


def run_update(sql: str, config: DeployConfig) -> None:
    completed = subprocess.run(
        compose_psql_command(ComposeConfig(config.compose_env, config.compose_file)),
        input=sql,
        text=True,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise InstagramWorkflowGuardError(
            "failed to update n8n workflow:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )


def fetch_status(config: DeployConfig) -> dict[str, Any]:
    completed = subprocess.run(
        compose_psql_command(
            ComposeConfig(config.compose_env, config.compose_file),
            "-At",
            "-c",
            build_status_query(config.workflow_id),
        ),
        text=True,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise InstagramWorkflowGuardError(
            "failed to fetch n8n workflow status:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    output = completed.stdout.strip()
    if not output:
        raise InstagramWorkflowGuardError(f"workflow not found in n8n: {config.workflow_id}")
    status = json.loads(output)
    if not isinstance(status, dict):
        raise InstagramWorkflowGuardError("status query did not return an object")
    return status


def validate_deployed_status(status: dict[str, Any], pin_data: dict[str, Any] | None) -> None:
    errors: list[str] = []
    if status.get("active") is not False:
        errors.append("active must be false")
    if status.get("has_instagram_ready_view") is not True:
        errors.append("instagram ready view must be present")
    if status.get("has_media_publish") is not True:
        errors.append("media_publish must be present")
    if status.get("has_waha") is not False:
        errors.append("WAHA must be absent")
    if status.get("history_exists") is not True:
        errors.append("current version must exist in workflow_history")
    if pin_data is not None and status.get("pinData") != pin_data:
        errors.append("deployed pinData does not match requested pinData")
    if errors:
        raise InstagramWorkflowGuardError("; ".join(errors))


def print_summary(status: dict[str, Any] | None, pin_data: dict[str, Any] | None) -> None:
    pin_mode = "preserve"
    if pin_data == SAFE_PINDATA:
        pin_mode = "safe"
    if pin_data == REAL_TEST_PINDATA:
        pin_mode = "instagram-real-test"
    if status is None:
        print("INFO | dry_run=true; no changes applied")
        print(f"INFO | pinData mode={pin_mode}")
        print("INFO | instagram workflow=ok")
        print("INFO | active=false")
        return
    print(f"INFO | workflow_id={status.get('id')}")
    print(f"INFO | versionId={status.get('versionId')}")
    print(f"INFO | versionCounter={status.get('versionCounter')}")
    print(f"INFO | active={str(status.get('active')).lower()}")
    print(f"INFO | pinData={pin_mode}")


def run(config: DeployConfig) -> int:
    workflow = load_workflow(config.workflow_json)
    validate_versioned_workflow(workflow, config.workflow_id)
    validate_pin_data(config.pin_data)
    sql = build_update_sql(workflow, config.workflow_id, config.pin_data)
    if config.dry_run:
        print_summary(None, config.pin_data)
        print(f"INFO | sql_bytes={len(sql.encode('utf-8'))}")
        return 0
    run_update(sql, config)
    status = fetch_status(config)
    validate_deployed_status(status, config.pin_data)
    print_summary(status, config.pin_data)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(config_from_args(parse_args(argv)))
    except (InstagramWorkflowGuardError, N8nOpsError, json.JSONDecodeError) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ops_common import (
    REAL_GROUP_PINDATA,
    SAFE_PINDATA,
    TEST_PHONE_PINDATA,
    ComposeConfig,
    N8nOpsError,
    compact_json,
    compose_psql_command,
    dollar_quote,
    resolve_mode,
    sql_literal,
)

DEFAULT_WORKFLOW_JSON = Path("n8n/workflows/ofertas-mvp-supabase.json")
DEFAULT_COMPOSE_ENV = Path("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE_FILE = Path("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
DEFAULT_WORKFLOW_ID = "OfertasMvpSupab1"
EXPECTED_TEMPLATE_TEXT = "Resgate o cupom desta pagina"
EXPECTED_SEND_IMAGE_PATH = "/api/sendImage"
FORBIDDEN_SEND_TEXT_PATH = "/api/sendText"
EXPECTED_SCHEDULE_CRON = "0 8-21 * * *"
EXPECTED_WORKFLOW_TIMEZONE = "America/Sao_Paulo"
EXPECTED_SCHEDULE_NODE = "Schedule Grupo Real"
EXPECTED_SCHEDULE_CONTEXT_NODE = "Set Contexto Schedule Grupo"
EXPECTED_SCHEDULE_LIMIT = 3
EXPECTED_SEND_DELAY_MIN = 45
EXPECTED_SEND_DELAY_MAX = 90
EXPECTED_LOOP_NODE = "Loop Ofertas"
EXPECTED_LOOP_RETURN_NODE = "Registrar Resultado Supabase"


class WorkflowGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeployConfig:
    workflow_json: Path
    workflow_id: str
    compose_env: Path
    compose_file: Path
    pin_data: dict[str, Any] | None
    dry_run: bool


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy and validate the guarded n8n workflow from the versioned JSON."
    )
    parser.add_argument("--workflow-json", type=Path, default=DEFAULT_WORKFLOW_JSON)
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--compose-env", type=Path, default=DEFAULT_COMPOSE_ENV)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print a summary without changing n8n.",
    )
    parser.add_argument(
        "--mode",
        choices=("grupo-real", "teste-telefone", "dry-run", "preserve-pindata"),
        default="grupo-real",
        help="Operational pinData mode. Defaults to grupo-real.",
    )
    pin_group = parser.add_mutually_exclusive_group()
    pin_group.add_argument(
        "--safe-pindata",
        action="store_true",
        help="Set pinData to dry_run=true/teste-whatsapp instead of the real group.",
    )
    pin_group.add_argument(
        "--preserve-pindata",
        action="store_true",
        help="Do not update the pinData stored in n8n.",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> DeployConfig:
    pin_data: dict[str, Any] | None
    if args.preserve_pindata:
        pin_data = None
    elif args.safe_pindata:
        pin_data = SAFE_PINDATA
    else:
        pin_data = resolve_mode(args.mode).pin_data
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
        raise WorkflowGuardError(f"workflow JSON not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowGuardError(f"invalid workflow JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WorkflowGuardError("workflow JSON must be an object")
    return payload


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


def validate_schedule(workflow: dict[str, Any], errors: list[str]) -> None:
    schedule_node = node_by_name(workflow, EXPECTED_SCHEDULE_NODE)
    if schedule_node is None:
        errors.append(f"missing schedule node: {EXPECTED_SCHEDULE_NODE}")
        return
    if schedule_node.get("type") != "n8n-nodes-base.scheduleTrigger":
        errors.append(f"{EXPECTED_SCHEDULE_NODE} must be scheduleTrigger")
    intervals = (
        schedule_node.get("parameters", {})
        .get("rule", {})
        .get("interval", [])
    )
    cron_expressions = [
        item.get("expression")
        for item in intervals
        if isinstance(item, dict) and item.get("field") == "cronExpression"
    ]
    if EXPECTED_SCHEDULE_CRON not in cron_expressions:
        errors.append(
            f"{EXPECTED_SCHEDULE_NODE} cron must include {EXPECTED_SCHEDULE_CRON}"
        )

    schedule_context = node_by_name(workflow, EXPECTED_SCHEDULE_CONTEXT_NODE)
    if schedule_context is None:
        errors.append(f"missing schedule context node: {EXPECTED_SCHEDULE_CONTEXT_NODE}")
    else:
        context_code = str(schedule_context.get("parameters", {}).get("jsCode", ""))
        for expected_text in (
            "dry_run: false",
            f"limit: {EXPECTED_SCHEDULE_LIMIT}",
            "target: 'grupo-ofertas-feminino'",
            "target_chat_id: '120363412864266334@g.us'",
            "allowed_targets_csv: 'grupo-ofertas-feminino'",
            f"send_delay_seconds_min: {EXPECTED_SEND_DELAY_MIN}",
            f"send_delay_seconds_max: {EXPECTED_SEND_DELAY_MAX}",
            "schedule-grupo-real",
        ):
            if expected_text not in context_code:
                errors.append(
                    f"{EXPECTED_SCHEDULE_CONTEXT_NODE} missing {expected_text}"
                )

    connections = workflow.get("connections")
    if isinstance(connections, dict):
        schedule_connections = json.dumps(
            connections.get(EXPECTED_SCHEDULE_NODE, {}),
            ensure_ascii=False,
        )
        context_connections = json.dumps(
            connections.get(EXPECTED_SCHEDULE_CONTEXT_NODE, {}),
            ensure_ascii=False,
        )
        if EXPECTED_SCHEDULE_CONTEXT_NODE not in schedule_connections:
            errors.append(
                f"{EXPECTED_SCHEDULE_NODE} must connect to {EXPECTED_SCHEDULE_CONTEXT_NODE}"
            )
        if "Validar Contexto" not in context_connections:
            errors.append(f"{EXPECTED_SCHEDULE_CONTEXT_NODE} must connect to Validar Contexto")

    settings = workflow.get("settings")
    if not isinstance(settings, dict) or settings.get("timezone") != EXPECTED_WORKFLOW_TIMEZONE:
        errors.append(f"workflow timezone must be {EXPECTED_WORKFLOW_TIMEZONE}")


def validate_send_loop(workflow: dict[str, Any], errors: list[str]) -> None:
    connections = workflow.get("connections")
    if not isinstance(connections, dict):
        return

    loop_main = connections.get(EXPECTED_LOOP_NODE, {}).get("main", [])
    loop_output = loop_main[1] if len(loop_main) > 1 else []
    if not any(
        connection.get("node") == "Montar Mensagens"
        for connection in loop_output
        if isinstance(connection, dict)
    ):
        errors.append(
            f"{EXPECTED_LOOP_NODE} loop output must connect to Montar Mensagens"
        )

    return_main = connections.get(EXPECTED_LOOP_RETURN_NODE, {}).get("main", [])
    return_output = return_main[0] if return_main else []
    if not any(
        connection.get("node") == EXPECTED_LOOP_NODE
        for connection in return_output
        if isinstance(connection, dict)
    ):
        errors.append(
            f"{EXPECTED_LOOP_RETURN_NODE} must connect back to {EXPECTED_LOOP_NODE}"
        )


def validate_versioned_workflow(workflow: dict[str, Any], workflow_id: str) -> None:
    errors: list[str] = []
    if workflow.get("id") != workflow_id:
        errors.append(f"workflow id mismatch: expected {workflow_id}, got {workflow.get('id')}")
    if not isinstance(workflow.get("nodes"), list):
        errors.append("workflow nodes must be a list")
    if not isinstance(workflow.get("connections"), dict):
        errors.append("workflow connections must be an object")

    text = workflow_text(workflow)
    if EXPECTED_SEND_IMAGE_PATH not in text:
        errors.append(f"missing {EXPECTED_SEND_IMAGE_PATH}")
    if FORBIDDEN_SEND_TEXT_PATH in text:
        errors.append(f"forbidden {FORBIDDEN_SEND_TEXT_PATH} found")
    if EXPECTED_TEMPLATE_TEXT not in text:
        errors.append(f"missing template text: {EXPECTED_TEMPLATE_TEXT}")

    validate_schedule(workflow, errors)
    validate_send_loop(workflow, errors)

    if errors:
        raise WorkflowGuardError("; ".join(errors))


def validate_pin_data(pin_data: dict[str, Any] | None) -> None:
    if pin_data is None:
        return
    try:
        payload = pin_data["Trigger Manual"][0]["json"]
    except (KeyError, IndexError, TypeError) as exc:
        raise WorkflowGuardError("pinData must contain Trigger Manual[0].json") from exc

    if not isinstance(payload.get("dry_run"), bool):
        raise WorkflowGuardError("pinData dry_run must be boolean")

    chat_id = payload.get("target_chat_id")
    if payload.get("dry_run") is False and not str(chat_id).endswith(("@g.us", "@c.us")):
        raise WorkflowGuardError("real pinData target_chat_id must end with @g.us or @c.us")


def build_update_sql(
    workflow: dict[str, Any],
    workflow_id: str,
    pin_data: dict[str, Any] | None,
) -> str:
    required_fields = ("nodes", "connections")
    missing = [field for field in required_fields if field not in workflow]
    if missing:
        raise WorkflowGuardError(f"workflow missing required fields: {missing}")

    assignments = [
        f"nodes = {dollar_quote(compact_json(workflow['nodes']))}::json",
        f"connections = {dollar_quote(compact_json(workflow['connections']))}::json",
        f"settings = {dollar_quote(compact_json(workflow.get('settings', {})))}::json",
        "active = false",
        '"versionId" = gen_random_uuid()::text',
        '"versionCounter" = coalesce("versionCounter", 0) + 1',
        '"updatedAt" = now()',
    ]
    if pin_data is not None:
        assignments.insert(
            3,
            f'"pinData" = {dollar_quote(compact_json(pin_data))}::json',
        )

    return (
        "update workflow_entity\n"
        f"set {', '.join(assignments)}\n"
        f"where id = {sql_literal(workflow_id)};"
    )


def build_status_query(workflow_id: str) -> str:
    return (
        "select json_build_object("
        "'id', id, "
        "'active', active, "
        "'versionId', \"versionId\", "
        "'versionCounter', \"versionCounter\", "
        "'updatedAt', \"updatedAt\", "
        "'has_new_copy', position('Resgate o cupom desta pagina' in nodes::text) > 0, "
        "'has_send_image', position('/api/sendImage' in nodes::text) > 0, "
        "'has_send_text', position('/api/sendText' in nodes::text) > 0, "
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
        raise WorkflowGuardError(
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
        raise WorkflowGuardError(
            "failed to fetch n8n workflow status:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    output = completed.stdout.strip()
    if not output:
        raise WorkflowGuardError(f"workflow not found in n8n: {config.workflow_id}")
    try:
        status = json.loads(output)
    except json.JSONDecodeError as exc:
        raise WorkflowGuardError(f"invalid status JSON from psql: {output}") from exc
    if not isinstance(status, dict):
        raise WorkflowGuardError("status query did not return an object")
    return status


def validate_deployed_status(status: dict[str, Any], pin_data: dict[str, Any] | None) -> None:
    errors: list[str] = []
    if status.get("active") is not False:
        errors.append("active must be false")
    if status.get("has_send_image") is not True:
        errors.append("sendImage must be present")
    if status.get("has_send_text") is not False:
        errors.append("sendText must be absent")
    if status.get("has_new_copy") is not True:
        errors.append(f"template must contain {EXPECTED_TEMPLATE_TEXT}")

    if pin_data is not None:
        deployed_pin_data = status.get("pinData")
        if deployed_pin_data != pin_data:
            errors.append("deployed pinData does not match requested pinData")
        else:
            try:
                payload = deployed_pin_data["Trigger Manual"][0]["json"]
            except (KeyError, IndexError, TypeError):
                errors.append("deployed pinData is malformed")
            else:
                if payload.get("dry_run") is not False and pin_data == REAL_GROUP_PINDATA:
                    errors.append("real group pinData must use dry_run=false")
                chat_id = payload.get("target_chat_id")
                if payload.get("dry_run") is False and not str(chat_id).endswith(
                    ("@g.us", "@c.us")
                ):
                    errors.append("real pinData target_chat_id must end with @g.us or @c.us")

    if errors:
        raise WorkflowGuardError("; ".join(errors))


def print_summary(status: dict[str, Any] | None, pin_data: dict[str, Any] | None) -> None:
    def pin_mode_name(value: dict[str, Any] | None) -> str:
        if value is None:
            return "preserve"
        if value == SAFE_PINDATA:
            return "safe"
        if value == TEST_PHONE_PINDATA:
            return "teste telefone"
        if value == REAL_GROUP_PINDATA:
            return "grupo real"
        return "custom"

    if status is None:
        mode = pin_mode_name(pin_data)
        print("INFO | dry_run=true; no changes applied")
        print(f"INFO | pinData mode={mode}")
        print("INFO | local workflow sendImage=ok")
        print("INFO | local workflow sendText=absent")
        print("INFO | local workflow template=ok")
        return

    pin_mode = pin_mode_name(status.get("pinData"))
    print(f"INFO | workflow_id={status.get('id')}")
    print(f"INFO | versionId={status.get('versionId')}")
    print(f"INFO | versionCounter={status.get('versionCounter')}")
    print(f"INFO | active={str(status.get('active')).lower()}")
    print("INFO | sendImage=ok")
    print("INFO | sendText=absent")
    print("INFO | template=ok")
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
    except (WorkflowGuardError, N8nOpsError) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

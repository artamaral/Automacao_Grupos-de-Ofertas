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
    REAL_GROUP_PINDATA,
    SAFE_PINDATA,
    TEST_PHONE_PINDATA,
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
EXPECTED_TEMPLATE_TEXT = "Resgate o cupom desta página"
EXPECTED_SEND_IMAGE_PATH = "/api/sendImage"
FORBIDDEN_SEND_TEXT_PATH = "/api/sendText"


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
        "'has_new_copy', position('Resgate o cupom desta página' in nodes::text) > 0, "
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

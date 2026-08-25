from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ops_common import ComposeConfig, N8nOpsError, compose_psql_command

DEFAULT_WORKFLOW_JSON = Path("n8n/workflows/ofertas-mvp-supabase-test-fanout.json")
DEFAULT_WORKFLOW_ID = "OfertasMvpSupab1-TestFanout"
DEFAULT_COMPOSE_ENV = Path("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE_FILE = Path("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
FORBIDDEN_VALUES = ("grupo-ofertas-feminino", "120363412864266334@g.us")
REQUIRED_DESTINATIONS = {
    "grupo-teste-fanout": ("N8N_TEST_FANOUT_GROUP_CHAT_ID", "group", "@g\\\\.us"),
    "canal-teste-fanout": ("N8N_TEST_FANOUT_CHANNEL_CHAT_ID", "channel", "@newsletter"),
}
FLOW_EXPANSIONS = {
    "recorrente": "Expandir Destinos Recorrente",
    "estatico": "Expandir Destinos Estatico",
    "pontual": "Expandir Destinos Pontual",
}


class WorkflowGuardError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or import the isolated test fan-out workflow."
    )
    parser.add_argument("--workflow-json", type=Path, default=DEFAULT_WORKFLOW_JSON)
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--compose-env", type=Path, default=DEFAULT_COMPOSE_ENV)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Update an existing manually imported clone and force it inactive.",
    )
    return parser.parse_args(argv)


def load_workflow(path: Path) -> dict[str, Any]:
    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowGuardError(f"workflow JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowGuardError(f"invalid workflow JSON: {path}: {exc}") from exc
    if not isinstance(workflow, dict):
        raise WorkflowGuardError("workflow JSON must be an object")
    return workflow


def node_by_name(workflow: dict[str, Any], name: str) -> dict[str, Any] | None:
    for node in workflow.get("nodes", []):
        if isinstance(node, dict) and node.get("name") == name:
            return node
    return None


def workflow_text(workflow: dict[str, Any]) -> str:
    return json.dumps(workflow, ensure_ascii=False, sort_keys=True)


def connection_targets(workflow: dict[str, Any], source: str, output: int = 0) -> set[str]:
    branches = workflow.get("connections", {}).get(source, {}).get("main", [])
    if not isinstance(branches, list) or len(branches) <= output:
        return set()
    return {
        str(connection.get("node"))
        for connection in branches[output]
        if isinstance(connection, dict) and connection.get("node")
    }


def validate_workflow(workflow: dict[str, Any], workflow_id: str = DEFAULT_WORKFLOW_ID) -> None:
    errors: list[str] = []
    text = workflow_text(workflow)
    node_names = {
        str(node.get("name")) for node in workflow.get("nodes", []) if isinstance(node, dict)
    }
    if workflow.get("id") != workflow_id:
        errors.append("workflow id mismatch")
    if workflow.get("active") is not False:
        errors.append("workflow active must be false")
    for value in FORBIDDEN_VALUES:
        if value in text:
            errors.append(f"forbidden production value found: {value}")
    for forbidden in (
        "/api/sendText",
        "offers.publication_events",
        "dispatch_status = 'claimed'",
        "for update of plan skip locked",
    ):
        if forbidden in text:
            errors.append(f"forbidden clone behavior found: {forbidden}")
    if "/api/sendImage" not in text:
        errors.append("missing /api/sendImage")
    if "N8N_TEST_FANOUT_REAL_SEND_ENABLED" not in text:
        errors.append("missing explicit real-send gate")
    for target, (env_name, kind, suffix) in REQUIRED_DESTINATIONS.items():
        for expected in (target, env_name, f"destination_kind: '{kind}'", suffix):
            if expected not in text:
                errors.append(f"destination contract missing {expected}")
    for flow, expansion in FLOW_EXPANSIONS.items():
        node = node_by_name(workflow, expansion)
        if node is None:
            errors.append(f"missing fan-out expansion for {flow}")
        elif node.get("parameters", {}).get("mode") != "runOnceForAllItems":
            errors.append(f"fan-out expansion must run once for all items: {flow}")
    for loop_name in (
        "Loop Destinos Recorrente",
        "Loop Destinos Estatico",
        "Loop Destinos Pontual",
    ):
        node = node_by_name(workflow, loop_name)
        if node is None or node.get("type") != "n8n-nodes-base.splitInBatches":
            errors.append(f"missing sequential destination loop: {loop_name}")
    expected_routes = {
        "Trigger Manual Estatico Fanout Teste": {"Resolver Sequencia Estatica"},
        "Trigger Manual Pontual Fanout Teste": {"Resolver Sequencia Pontual"},
        "Configurar Destinos Fanout Teste": {
            "IF Fluxo Recorrente Fanout",
            "IF Fluxo Estatico Fanout",
            "IF Fluxo Pontual Fanout",
        },
        "IF Fluxo Recorrente Fanout": {"Validar Contexto"},
        "IF Fluxo Estatico Fanout": {"Buscar Pasta Raiz Drive"},
        "IF Fluxo Pontual Fanout": {"Buscar Pasta Pendentes Drive Pontual"},
        "Expandir Destinos Recorrente": {"Loop Destinos Recorrente"},
        "Expandir Destinos Estatico": {"Loop Destinos Estatico"},
        "Expandir Destinos Pontual": {"Loop Destinos Pontual"},
        "Normalizar Resultado WAHA": {"Loop Destinos Recorrente"},
        "Normalizar Resultado WAHA Estatico": {"Loop Destinos Estatico"},
        "Normalizar Resultado WAHA Pontual": {"Loop Destinos Pontual"},
    }
    for source, expected in expected_routes.items():
        if not expected <= connection_targets(workflow, source):
            errors.append(f"fan-out connection missing from {source}")
    for manual_name in (
        "Trigger Manual Estatico Fanout Teste",
        "Trigger Manual Pontual Fanout Teste",
    ):
        node = node_by_name(workflow, manual_name)
        if node is None or node.get("type") != "n8n-nodes-base.manualTrigger":
            errors.append(f"missing isolated manual trigger: {manual_name}")
    if "Loop Ofertas" not in connection_targets(workflow, "Loop Destinos Recorrente"):
        errors.append("recurring destination loop must return to offer loop")
    for source, connection in workflow.get("connections", {}).items():
        if source not in node_names:
            errors.append(f"connection source does not reference a node: {source}")
        for branch in connection.get("main", []) if isinstance(connection, dict) else []:
            for target in branch:
                if isinstance(target, dict) and target.get("node") not in node_names:
                    errors.append(
                        f"connection target does not reference a node: {target.get('node')}"
                    )
    if node_by_name(workflow, "Registrar Resultado Supabase") is not None:
        errors.append("recurring ledger node must be absent")
    if node_by_name(workflow, "Registrar Resultado Supabase Estatico") is not None:
        errors.append("static ledger node must be absent")
    if node_by_name(workflow, "Registrar Resultado Supabase Pontual") is not None:
        errors.append("one-shot ledger node must be absent")
    if node_by_name(workflow, "Mover Pasta msg_XXX Pontual") is not None:
        errors.append("one-shot archive node must be absent")
    if errors:
        raise WorkflowGuardError("; ".join(errors))


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def dollar_quote(value: str) -> str:
    return "$workflow$" + value.replace("$workflow$", "$workflow_x$") + "$workflow$"


def build_update_sql(workflow: dict[str, Any], workflow_id: str) -> str:
    nodes = json.dumps(workflow["nodes"], ensure_ascii=False, separators=(",", ":"))
    connections = json.dumps(workflow["connections"], ensure_ascii=False, separators=(",", ":"))
    settings = json.dumps(workflow.get("settings", {}), ensure_ascii=False, separators=(",", ":"))
    return (
        "with updated_workflow as (\n"
        "  update workflow_entity\n"
        f"  set nodes = {dollar_quote(nodes)}::json,\n"
        f"      connections = {dollar_quote(connections)}::json,\n"
        f"      settings = {dollar_quote(settings)}::json,\n"
        "      active = false,\n"
        '      "versionId" = gen_random_uuid()::text,\n'
        '      "versionCounter" = coalesce("versionCounter", 0) + 1,\n'
        '      "updatedAt" = now()\n'
        f"  where id = {sql_literal(workflow_id)}\n"
        '  returning id, "versionId", name, nodes, connections, "updatedAt"\n'
        ")\n"
        "insert into workflow_history (\n"
        '  "versionId", "workflowId", authors, "createdAt", "updatedAt",\n'
        '  nodes, connections, name, autosaved, description, "nodeGroups"\n'
        ")\n"
        "select\n"
        '  updated."versionId", updated.id,\n'
        "  coalesce((\n"
        "    select history.authors\n"
        "    from workflow_history history\n"
        '    where history."workflowId" = updated.id\n'
        '    order by history."createdAt" desc\n'
        "    limit 1\n"
        "  ), 'system'),\n"
        '  updated."updatedAt", updated."updatedAt", updated.nodes,\n'
        "  updated.connections, updated.name, false, null, '[]'::json\n"
        "from updated_workflow updated\n"
        'returning "workflowId" as id;'
    )


def apply_workflow(sql: str, args: argparse.Namespace) -> None:
    completed = subprocess.run(
        compose_psql_command(ComposeConfig(args.compose_env, args.compose_file)),
        input=sql,
        text=True,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no psql diagnostic"
        raise WorkflowGuardError(f"failed to update the imported test fan-out workflow: {detail}")
    if not completed.stdout.strip():
        raise WorkflowGuardError(
            "workflow was not updated inactive; import it in the n8n panel first"
        )


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    workflow = load_workflow(args.workflow_json)
    validate_workflow(workflow, args.workflow_id)
    sql = build_update_sql(workflow, args.workflow_id)
    if args.apply:
        apply_workflow(sql, args)
        print(f"INFO | workflow_id={args.workflow_id}")
        print("INFO | active=false")
        print("INFO | imported clone fan-out updated")
    else:
        print("INFO | dry_run=true; no changes applied")
        print("INFO | clone fan-out contract=ok")
        print(f"INFO | sql_bytes={len(sql.encode('utf-8'))}")
    return 0


def main() -> int:
    try:
        return run()
    except (WorkflowGuardError, N8nOpsError) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import base64
import json
import subprocess
from pathlib import Path, PurePosixPath

# Remote SQL is intentionally composed as one command for the VPS transaction.
# ruff: noqa: E501


DEFAULT_HOST = "hostinger-n8n"
DEFAULT_WORKFLOW_JSON = Path("n8n/workflows/ofertas-instagram-reels-render-draft.json")
DEFAULT_N8N_ENV = PurePosixPath("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE = PurePosixPath("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
WORKFLOW_ID = "OfertasInstagramReelsRenderDraft"


REMOTE_SCRIPT = r'''
import json
import subprocess
import sys

payload = json.load(sys.stdin)
workflow = payload["workflow"]
workflow_id = payload["workflow_id"]
n8n_env = payload["n8n_env"]
compose_file = payload["compose_file"]
inspect = payload.get("inspect", False)

if workflow.get("id") != workflow_id:
    raise SystemExit("WORKFLOW_ID_MISMATCH")
if workflow.get("active") is not False:
    raise SystemExit("WORKFLOW_MUST_BE_INACTIVE")
if not workflow.get("nodes") or not workflow.get("connections"):
    raise SystemExit("WORKFLOW_STRUCTURE_INVALID")

def dq(value):
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if "$codex$" in encoded:
        raise SystemExit("SQL_DELIMITER_COLLISION")
    return "$codex$" + encoded + "$codex$"

def sql(value):
    return "'" + str(value).replace("'", "''") + "'"

compose = ["docker", "compose", "--env-file", n8n_env, "-f", compose_file, "exec", "-T", "postgres", "psql", "-U", "n8n", "-d", "n8n", "-At", "-v", "ON_ERROR_STOP=1"]
if inspect:
    inspect_sql = "select json_build_object('id', id, 'name', name, 'active', active, 'node_count', jsonb_array_length(nodes::jsonb), 'has_renderer_url', position('/v1/render/jobs' in nodes::text) > 0, 'has_drive_credential', position('mpDU88mNaqYR5jzz' in nodes::text) > 0)::text from workflow_entity where id = " + sql(workflow_id) + ";"
    inspected = subprocess.run(compose + ["-c", inspect_sql], text=True, capture_output=True, check=False)
    if inspected.returncode != 0 or not inspected.stdout.strip():
        raise SystemExit("INSPECT_FAILED=" + (inspected.stderr.strip() or inspected.stdout.strip()))
    print(inspected.stdout.strip().splitlines()[-1])
    raise SystemExit(0)
project_sql = "select sw.\"projectId\" from shared_workflow sw order by sw.\"updatedAt\" desc limit 1;"
project = subprocess.run(compose + ["-c", project_sql], text=True, capture_output=True, check=False)
if project.returncode != 0 or not project.stdout.strip():
    raise SystemExit("PROJECT_ID_NOT_FOUND=" + (project.stderr.strip() or project.stdout.strip()))

nodes = dq(workflow["nodes"])
connections = dq(workflow["connections"])
settings = dq(workflow.get("settings", {}))
pin_data = dq(workflow.get("pinData", {}))
name = sql(workflow.get("name") or workflow_id)
wid = sql(workflow_id)
sql_text = f"""
with upserted as (
  insert into workflow_entity (id, name, active, nodes, connections, settings, \"pinData\", \"versionId\", \"versionCounter\", \"nodeGroups\")
  values ({wid}, {name}, false, {nodes}::json, {connections}::json, {settings}::json, {pin_data}::json, gen_random_uuid()::text, 1, '[]'::json)
  on conflict (id) do update set
    name = excluded.name,
    nodes = excluded.nodes,
    connections = excluded.connections,
    settings = excluded.settings,
    \"pinData\" = excluded.\"pinData\",
    active = false,
    \"versionId\" = gen_random_uuid()::text,
    \"versionCounter\" = coalesce(workflow_entity.\"versionCounter\", 0) + 1,
    \"updatedAt\" = now()
  returning id, \"versionId\", name, nodes, connections, \"updatedAt\"
), project as (
  select sw.\"projectId\" from shared_workflow sw order by sw.\"updatedAt\" desc limit 1
), shared as (
  insert into shared_workflow (\"workflowId\", \"projectId\", role)
  select upserted.id, project.\"projectId\", 'workflow:owner' from upserted cross join project
  on conflict (\"workflowId\", \"projectId\") do nothing
), history as (
  insert into workflow_history (\"versionId\", \"workflowId\", authors, \"createdAt\", \"updatedAt\", nodes, connections, name, autosaved, description, \"nodeGroups\")
  select upserted.\"versionId\", upserted.id, 'codex', upserted.\"updatedAt\", upserted.\"updatedAt\", upserted.nodes, upserted.connections, upserted.name, false, null, '[]'::json from upserted
)
select json_build_object('id', id, 'active', active, 'versionCounter', \"versionCounter\", 'updatedAt', \"updatedAt\")::text from workflow_entity where id = {wid};
"""
result = subprocess.run(compose + ["-c", sql_text], text=True, capture_output=True, check=False)
if result.returncode != 0:
    raise SystemExit("UPSERT_FAILED=" + (result.stderr.strip() or result.stdout.strip()))
status_sql = 'select json_build_object(\'id\', id, \'active\', active, \'versionCounter\', "versionCounter", \'updatedAt\', "updatedAt")::text from workflow_entity where id = ' + wid + ';'
status = subprocess.run(
    compose + ["-c", status_sql],
    text=True,
    capture_output=True,
    check=False,
)
if status.returncode != 0 or not status.stdout.strip():
    raise SystemExit("STATUS_FAILED=" + (status.stderr.strip() or status.stdout.strip()))
print(status.stdout.strip().splitlines()[-1])
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importa o draft de render Reels no n8n como workflow inativo.")
    parser.add_argument("--workflow-json", type=Path, default=DEFAULT_WORKFLOW_JSON)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--n8n-env", default=str(DEFAULT_N8N_ENV))
    parser.add_argument("--compose-file", default=str(DEFAULT_COMPOSE))
    parser.add_argument("--confirm-remote-write")
    parser.add_argument("--inspect", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.inspect and args.confirm_remote_write:
        raise SystemExit("--inspect e --confirm-remote-write sao mutuamente exclusivos")
    if not args.inspect and args.confirm_remote_write != "IMPORT_INACTIVE_REELS_RENDER_DRAFT":
        raise SystemExit("confirmacao obrigatoria: IMPORT_INACTIVE_REELS_RENDER_DRAFT")
    workflow = json.loads(args.workflow_json.read_text(encoding="utf-8"))
    if not args.inspect and (workflow.get("id") != WORKFLOW_ID or workflow.get("active") is not False):
        raise SystemExit("draft invalido: ID ou active inesperado")
    encoded = base64.b64encode(REMOTE_SCRIPT.encode("utf-8")).decode("ascii")
    command = f"python3 -c \"import base64; exec(base64.b64decode('{encoded}'))\""
    payload = json.dumps({"workflow": workflow, "workflow_id": WORKFLOW_ID, "n8n_env": args.n8n_env, "compose_file": args.compose_file, "inspect": args.inspect}, ensure_ascii=False, separators=(",", ":"))
    result = subprocess.run(
        ["ssh", args.host, command],
        input=payload,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "remote deploy failed")
    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

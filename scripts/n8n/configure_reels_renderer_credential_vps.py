from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# Remote SQL and n8n CLI commands intentionally contain long command lines.
# ruff: noqa: E501


CONFIRMATION = "CREATE_REELS_RENDERER_CREDENTIAL"
DEFAULT_HOST = "hostinger-n8n"
DEFAULT_RENDER_ENV = PurePosixPath("/opt/automacao_grupo_compras/reels-media/.env")
DEFAULT_N8N_ENV = PurePosixPath("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE = PurePosixPath("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
CREDENTIAL_ID = "reelsRendererBearer1"
CREDENTIAL_NAME = "Reels Renderer Bearer"
DRIVE_CREDENTIAL_NAME = "Google Drive account"
WORKFLOW_ID = "OfertasInstagramSupab1"


REMOTE_SCRIPT = r'''
import json
import subprocess
from pathlib import Path

payload = json.load(__import__("sys").stdin)
render_env = Path(payload["render_env"])
n8n_env = Path(payload["n8n_env"])
compose_file = Path(payload["compose_file"])
credential_id = payload["credential_id"]
credential_name = payload["credential_name"]
drive_name = payload["drive_name"]
workflow_id = payload["workflow_id"]
apply = payload["apply"]

for required in (render_env, n8n_env, compose_file):
    if not required.exists():
        raise SystemExit(f"FILE_NOT_FOUND={required}")

values = {}
for raw in render_env.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
token = values.get("REELS_RENDER_API_TOKEN", "")
if len(token) < 32 or any(char.isspace() for char in token):
    raise SystemExit("RENDER_TOKEN_INVALID")

compose_prefix = ["docker", "compose", "--env-file", str(n8n_env), "-f", str(compose_file), "exec", "-T"]

def psql(sql):
    result = subprocess.run(
        compose_prefix + ["postgres", "psql", "-U", "n8n", "-d", "n8n", "-At", "-v", "ON_ERROR_STOP=1", "-c", sql],
        text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        raise SystemExit("PSQL_FAILED=" + result.stderr.strip())
    return result.stdout.strip()

renderer = psql(
    "select id || E'|' || name || E'|' || type from credentials_entity "
    f"where id = '{credential_id}' or name in ('{credential_name}', '{drive_name}') "
    "order by \"updatedAt\" desc nulls last;"
)
drive_lines = [line for line in renderer.splitlines() if f"|{drive_name}|" in line]
drive_found = bool(drive_lines)
drive_id = drive_lines[0].split("|", 1)[0] if drive_lines else ""
project_id = psql(
    "select sw.\"projectId\" from shared_workflow sw "
    f"where sw.\"workflowId\" = '{workflow_id}' limit 1;"
)
if not project_id:
    raise SystemExit("PROJECT_ID_NOT_FOUND")

report = {"renderer_credential_found": credential_id in renderer or credential_name in renderer,
          "google_drive_credential_found": drive_found, "google_drive_credential_id": drive_id,
          "project_id_found": bool(project_id)}
if not apply:
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0)

existing_id = psql(
    "select id from credentials_entity "
    f"where id = '{credential_id}' or (name = '{credential_name}' and type = 'httpHeaderAuth') "
    "order by \"updatedAt\" desc nulls last limit 1;"
)
if existing_id:
    deleted = subprocess.run(
        compose_prefix + ["n8n", "n8n", "delete:credentials", f"--id={existing_id}"],
        text=True, capture_output=True, check=False,
    )
    if deleted.returncode != 0:
        psql(
            "do $$ begin "
            "if exists (select 1 from information_schema.tables where table_schema='public' and table_name='shared_credentials') then "
            f"delete from shared_credentials where \"credentialsId\"='{existing_id}'; end if; "
            f"delete from credentials_entity where id='{existing_id}'; end $$;"
        )

credential = [{"id": credential_id, "name": credential_name, "type": "httpHeaderAuth",
               "data": {"name": "Authorization", "value": f"Bearer {token}"}}]
import_file = "/tmp/reels-renderer-credential.json"
completed = subprocess.run(
    compose_prefix + ["n8n", "sh", "-lc", f"cat > {import_file} && n8n import:credentials --input={import_file} --projectId={project_id}"],
    input=json.dumps(credential), text=True, capture_output=True, check=False,
)
if completed.returncode != 0:
    raise SystemExit("IMPORT_FAILED=" + (completed.stderr.strip() or completed.stdout.strip()))
print(json.dumps({**report, "renderer_credential_created": True}, ensure_ascii=False))
'''


class CredentialConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    host: str
    ssh_bin: Path | str
    render_env: PurePosixPath
    n8n_env: PurePosixPath
    compose_file: PurePosixPath
    apply: bool
    inspect: bool
    confirmation: str | None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configura a credencial do renderer Reels no n8n sem expor o token.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-bin", type=Path, default=Path(r"C:\Windows\System32\OpenSSH\ssh.exe"))
    parser.add_argument("--render-env", default=str(DEFAULT_RENDER_ENV))
    parser.add_argument("--n8n-env", default=str(DEFAULT_N8N_ENV))
    parser.add_argument("--compose-file", default=str(DEFAULT_COMPOSE))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--confirm-remote-write")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> Config:
    return Config(
        host=str(args.host).strip(),
        ssh_bin=args.ssh_bin,
        render_env=PurePosixPath(str(args.render_env).strip()),
        n8n_env=PurePosixPath(str(args.n8n_env).strip()),
        compose_file=PurePosixPath(str(args.compose_file).strip()),
        apply=bool(args.apply),
        inspect=bool(args.inspect),
        confirmation=args.confirm_remote_write,
    )


def validate(config: Config) -> None:
    if not config.host or any(char.isspace() for char in config.host):
        raise CredentialConfigError("host SSH invalido")
    for path in (config.render_env, config.n8n_env, config.compose_file):
        if not str(path).startswith("/"):
            raise CredentialConfigError("caminhos remotos devem ser absolutos")
    if config.apply and config.inspect:
        raise CredentialConfigError("--apply e --inspect sao mutuamente exclusivos")
    if config.apply and config.confirmation != CONFIRMATION:
        raise CredentialConfigError(f"confirmacao obrigatoria: {CONFIRMATION}")


def remote_command() -> str:
    encoded = base64.b64encode(REMOTE_SCRIPT.encode("utf-8")).decode("ascii")
    return f"python3 -c \"import base64; exec(base64.b64decode('{encoded}'))\""


def run(config: Config) -> int:
    validate(config)
    payload = json.dumps(
        {"render_env": str(config.render_env), "n8n_env": str(config.n8n_env),
         "compose_file": str(config.compose_file), "credential_id": CREDENTIAL_ID,
         "credential_name": CREDENTIAL_NAME, "drive_name": DRIVE_CREDENTIAL_NAME,
         "workflow_id": WORKFLOW_ID, "apply": config.apply},
        separators=(",", ":"),
    )
    completed = subprocess.run(
        [str(config.ssh_bin), config.host, remote_command()],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise CredentialConfigError(completed.stderr.strip() or completed.stdout.strip())
    print(completed.stdout.strip())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run(config_from_args(parse_args())))
    except CredentialConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

CONFIRMATION = "CREATE_INSTAGRAM_HTTP_CREDENTIAL"
DEFAULT_HOST = "hostinger-n8n"
DEFAULT_REMOTE_ENV = PurePosixPath("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE_FILE = PurePosixPath("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
DEFAULT_WORKFLOW_ID = "OfertasInstagramSupab1"
DEFAULT_CREDENTIAL_ID = "instagramGraphHdrAuth1"
DEFAULT_CREDENTIAL_NAME = "Instagram Graph Bearer"

REMOTE_SCRIPT = r"""
import json
import subprocess
import sys
from pathlib import Path

payload = json.load(sys.stdin)
remote_env = Path(payload["remote_env"])
compose_file = Path(payload["compose_file"])
workflow_id = payload["workflow_id"]
project_id = payload.get("project_id")
credential_id = payload["credential_id"]
credential_name = payload["credential_name"]

if not remote_env.exists():
    raise SystemExit(f"REMOTE_ENV_NOT_FOUND={remote_env}")
if not compose_file.exists():
    raise SystemExit(f"COMPOSE_FILE_NOT_FOUND={compose_file}")

env_values = {}
for raw_line in remote_env.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    env_values[key.strip()] = value.strip()

access_token = env_values.get("INSTAGRAM_ACCESS_TOKEN", "")
if len(access_token) < 20 or any(character.isspace() for character in access_token):
    raise SystemExit("INSTAGRAM_ACCESS_TOKEN_INVALID")

compose_prefix = [
    "docker",
    "compose",
    "--env-file",
    str(remote_env),
    "-f",
    str(compose_file),
    "exec",
    "-T",
]

def run_psql(sql: str) -> str:
    completed = subprocess.run(
        compose_prefix
        + [
            "postgres",
            "psql",
            "-U",
            "n8n",
            "-d",
            "n8n",
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(f"PSQL_FAILED={completed.stderr.strip()}")
    return completed.stdout.strip()

existing = run_psql(
    "select id from credentials_entity "
    f"where id = '{credential_id}' or (name = '{credential_name}' and type = 'httpHeaderAuth') limit 1;"
)
if existing:
    print(f"CREDENTIAL_EXISTS={existing}")
    raise SystemExit(0)

if not project_id:
    project_id = run_psql(
        "select sw.\"projectId\" from shared_workflow sw "
        f"where sw.\"workflowId\" = '{workflow_id}' limit 1;"
    )
if not project_id:
    raise SystemExit("PROJECT_ID_NOT_FOUND")

credential_payload = [
    {
        "id": credential_id,
        "name": credential_name,
        "type": "httpHeaderAuth",
        "data": {
            "name": "Authorization",
            "value": f"Bearer {access_token}",
        },
    }
]
credential_file = "/tmp/instagram-http-credential.json"
completed = subprocess.run(
    compose_prefix
    + [
        "n8n",
        "sh",
        "-lc",
        f"cat > {credential_file} && n8n import:credentials --input={credential_file} --projectId={project_id}",
    ],
    input=json.dumps(credential_payload),
    text=True,
    capture_output=True,
    check=False,
)
if completed.returncode != 0:
    raise SystemExit(f"IMPORT_FAILED={completed.stderr.strip() or completed.stdout.strip()}")

print(f"CREDENTIAL_CREATED={credential_id}")
print(f"PROJECT_ID={project_id}")
"""


class InstagramHttpCredentialError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    host: str
    ssh_bin: Path | str
    remote_env: PurePosixPath
    compose_file: PurePosixPath
    workflow_id: str
    credential_id: str
    credential_name: str
    project_id: str | None
    apply: bool
    confirmation: str | None


def default_ssh_bin() -> Path | str:
    if sys.platform.startswith("win"):
        windows_ssh = Path(r"C:\Windows\System32\OpenSSH\ssh.exe")
        if windows_ssh.is_file():
            return windows_ssh
    return "ssh"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Cria a credencial httpHeaderAuth do Instagram no n8n usando o token "
            "ja presente no .env remoto, sem imprimir segredos."
        )
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-bin", type=Path, default=default_ssh_bin())
    parser.add_argument("--remote-env", default=str(DEFAULT_REMOTE_ENV))
    parser.add_argument("--compose-file", default=str(DEFAULT_COMPOSE_FILE))
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--credential-id", default=DEFAULT_CREDENTIAL_ID)
    parser.add_argument("--credential-name", default=DEFAULT_CREDENTIAL_NAME)
    parser.add_argument("--project-id")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> Config:
    return Config(
        host=str(args.host).strip(),
        ssh_bin=args.ssh_bin,
        remote_env=PurePosixPath(str(args.remote_env).strip()),
        compose_file=PurePosixPath(str(args.compose_file).strip()),
        workflow_id=str(args.workflow_id).strip(),
        credential_id=str(args.credential_id).strip(),
        credential_name=str(args.credential_name).strip(),
        project_id=(str(args.project_id).strip() if args.project_id else None),
        apply=bool(args.apply),
        confirmation=args.confirm_remote_write,
    )


def validate_config(config: Config) -> None:
    if not config.host or any(character.isspace() for character in config.host):
        raise InstagramHttpCredentialError("host SSH invalido")
    if not str(config.remote_env).startswith("/"):
        raise InstagramHttpCredentialError("remote-env deve ser um caminho absoluto POSIX")
    if not str(config.compose_file).startswith("/"):
        raise InstagramHttpCredentialError("compose-file deve ser um caminho absoluto POSIX")
    if not config.workflow_id:
        raise InstagramHttpCredentialError("workflow-id obrigatorio")
    if not config.credential_id:
        raise InstagramHttpCredentialError("credential-id obrigatorio")
    if not config.credential_name:
        raise InstagramHttpCredentialError("credential-name obrigatorio")
    if config.apply and config.confirmation != CONFIRMATION:
        raise InstagramHttpCredentialError(
            f"--confirm-remote-write deve ser exatamente {CONFIRMATION}"
        )


def ssh_command(config: Config, remote_command: str) -> list[str]:
    return [str(config.ssh_bin), config.host, remote_command]


def build_payload(config: Config) -> str:
    return json.dumps(
        {
            "remote_env": str(config.remote_env),
            "compose_file": str(config.compose_file),
            "workflow_id": config.workflow_id,
            "project_id": config.project_id,
            "credential_id": config.credential_id,
            "credential_name": config.credential_name,
        },
        separators=(",", ":"),
    )


def remote_python_command() -> str:
    encoded = base64.b64encode(REMOTE_SCRIPT.encode("utf-8")).decode("ascii")
    return f"python3 -c \"import base64; exec(base64.b64decode('{encoded}'))\""


def print_dry_run(config: Config) -> None:
    resolved_project = config.project_id or f"<workflow:{config.workflow_id}>"
    print("INFO | dry_run=true; no changes applied")
    print(f"INFO | credential_id={config.credential_id}")
    print(f"INFO | credential_name={config.credential_name}")
    print(f"INFO | project_id={resolved_project}")
    print(f"INFO | remote_env={config.remote_env}")


def run(config: Config) -> int:
    validate_config(config)
    if not config.apply:
        print_dry_run(config)
        return 0
    payload = build_payload(config)
    output = subprocess.run(
        ssh_command(config, remote_python_command()),
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if output.returncode != 0:
        raise InstagramHttpCredentialError(
            "comando remoto falhou; "
            f"codigo={output.returncode}; stderr={output.stderr.strip()}"
        )
    if output.stdout.strip():
        print(output.stdout.strip())
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(config_from_args(parse_args(argv)))
    except InstagramHttpCredentialError as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

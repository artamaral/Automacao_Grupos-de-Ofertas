from __future__ import annotations

import argparse
import getpass
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

CONFIRMATION = "UPDATE_INSTAGRAM_ENV"
DEFAULT_HOST = "hostinger-n8n"
DEFAULT_REMOTE_ENV = PurePosixPath("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE_FILE = PurePosixPath("/opt/automacao_grupo_compras/n8n/docker-compose.yml")

REMOTE_SCRIPT = r"""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

payload = json.load(sys.stdin)
target = Path(payload["remote_env"])
compose_file = Path(payload["compose_file"])
restart_n8n = bool(payload["restart_n8n"])
values = payload["values"]

if not target.exists():
    raise SystemExit(f"REMOTE_ENV_NOT_FOUND={target}")
if not compose_file.exists():
    raise SystemExit(f"COMPOSE_FILE_NOT_FOUND={compose_file}")

original_stat = target.stat()
lines = target.read_text(encoding="utf-8").splitlines()
seen = set()
updated = []
for line in lines:
    replaced = False
    for key, value in values.items():
        if line.startswith(f"{key}="):
            updated.append(f"{key}={value}")
            seen.add(key)
            replaced = True
            break
    if not replaced:
        updated.append(line)

if updated and updated[-1].strip():
    updated.append("")
for key, value in values.items():
    if key not in seen:
        updated.append(f"{key}={value}")

backup = target.with_suffix(target.suffix + ".instagram.bak")
shutil.copy2(target, backup)
tmp = target.with_suffix(target.suffix + ".instagram.tmp")
tmp.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
os.chmod(tmp, stat.S_IMODE(original_stat.st_mode))
try:
    os.chown(tmp, original_stat.st_uid, original_stat.st_gid)
except PermissionError:
    pass
os.replace(tmp, target)

print(f"UPDATED_ENV mode={stat.S_IMODE(target.stat().st_mode):o} bytes={target.stat().st_size}")
print(f"BACKUP_ENV mode={stat.S_IMODE(backup.stat().st_mode):o} bytes={backup.stat().st_size}")

if restart_n8n:
    subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(target),
            "-f",
            str(compose_file),
            "up",
            "-d",
        ],
        check=True,
    )
    print("N8N_RESTART=OK")
else:
    print("N8N_RESTART=SKIPPED")
"""


class InstagramEnvConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateConfig:
    host: str
    ssh_bin: Path | str
    remote_env: PurePosixPath
    compose_file: PurePosixPath
    apply: bool
    confirmation: str | None
    restart_n8n: bool


def default_ssh_bin() -> Path | str:
    if os.name == "nt":
        windows_ssh = Path(os.environ.get("WINDIR", r"C:\Windows")) / (
            "System32/OpenSSH/ssh.exe"
        )
        if windows_ssh.is_file():
            return windows_ssh
    return "ssh"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Configura INSTAGRAM_ACCESS_TOKEN e INSTAGRAM_BUSINESS_ACCOUNT_ID "
            "no .env do n8n na VPS sem imprimir segredos."
        )
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-bin", type=Path, default=default_ssh_bin())
    parser.add_argument("--remote-env", default=str(DEFAULT_REMOTE_ENV))
    parser.add_argument("--compose-file", default=str(DEFAULT_COMPOSE_FILE))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restart-n8n", action="store_true")
    parser.add_argument("--confirm-remote-write")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> UpdateConfig:
    return UpdateConfig(
        host=str(args.host).strip(),
        ssh_bin=args.ssh_bin,
        remote_env=PurePosixPath(str(args.remote_env).strip()),
        compose_file=PurePosixPath(str(args.compose_file).strip()),
        apply=bool(args.apply),
        confirmation=args.confirm_remote_write,
        restart_n8n=bool(args.restart_n8n),
    )


def validate_config(config: UpdateConfig) -> None:
    if not config.host or any(character.isspace() for character in config.host):
        raise InstagramEnvConfigError("host SSH invalido")
    if not str(config.remote_env).startswith("/"):
        raise InstagramEnvConfigError("remote-env deve ser um caminho absoluto POSIX")
    if not str(config.compose_file).startswith("/"):
        raise InstagramEnvConfigError("compose-file deve ser um caminho absoluto POSIX")
    if config.apply and config.confirmation != CONFIRMATION:
        raise InstagramEnvConfigError(
            f"--confirm-remote-write deve ser exatamente {CONFIRMATION}"
        )


def validate_instagram_values(access_token: str, business_account_id: str) -> None:
    if not access_token or len(access_token.strip()) < 20:
        raise InstagramEnvConfigError("INSTAGRAM_ACCESS_TOKEN parece vazio ou curto demais")
    if any(character.isspace() for character in access_token):
        raise InstagramEnvConfigError("INSTAGRAM_ACCESS_TOKEN nao deve conter espacos/quebras")
    if not business_account_id.isdigit():
        raise InstagramEnvConfigError("INSTAGRAM_BUSINESS_ACCOUNT_ID deve conter apenas digitos")


def ssh_command(config: UpdateConfig, remote_command: str) -> list[str]:
    return [str(config.ssh_bin), config.host, remote_command]


def run_ssh(
    config: UpdateConfig,
    remote_command: str,
    *,
    payload: str | None = None,
) -> str:
    completed = subprocess.run(
        ssh_command(config, remote_command),
        input=payload,
        text=True,
        check=False,
        capture_output=True,
        timeout=60,
    )
    if completed.returncode != 0:
        raise InstagramEnvConfigError(
            "comando SSH falhou; "
            f"codigo={completed.returncode}; stderr={completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def build_payload(
    config: UpdateConfig,
    *,
    access_token: str,
    business_account_id: str,
) -> str:
    return json.dumps(
        {
            "remote_env": str(config.remote_env),
            "compose_file": str(config.compose_file),
            "restart_n8n": config.restart_n8n,
            "values": {
                "INSTAGRAM_ACCESS_TOKEN": access_token,
                "INSTAGRAM_BUSINESS_ACCOUNT_ID": business_account_id,
            },
        },
        separators=(",", ":"),
    )


def inspect_remote(config: UpdateConfig) -> str:
    return run_ssh(
        config,
        (
            "if test -f "
            f"{str(config.remote_env)!r}"
            "; then "
            f"stat -c 'REMOTE_ENV mode=%a owner=%U group=%G bytes=%s' {str(config.remote_env)!r}; "
            "else echo REMOTE_ENV=missing; fi; "
            f"if grep -q '^INSTAGRAM_ACCESS_TOKEN=' {str(config.remote_env)!r}; "
            "then echo INSTAGRAM_ACCESS_TOKEN=present; "
            "else echo INSTAGRAM_ACCESS_TOKEN=missing; fi; "
            f"if grep -q '^INSTAGRAM_BUSINESS_ACCOUNT_ID=' {str(config.remote_env)!r}; "
            "then echo INSTAGRAM_BUSINESS_ACCOUNT_ID=present; "
            "else echo INSTAGRAM_BUSINESS_ACCOUNT_ID=missing; fi"
        ),
    )


def run(
    config: UpdateConfig,
    *,
    access_token: str | None = None,
    business_account_id: str | None = None,
) -> int:
    validate_config(config)
    if not config.apply:
        print(inspect_remote(config))
        print("DRY_RUN=true; nenhum segredo foi alterado")
        return 0

    resolved_access_token = access_token or getpass.getpass("INSTAGRAM_ACCESS_TOKEN: ").strip()
    resolved_business_account_id = (
        business_account_id or getpass.getpass("INSTAGRAM_BUSINESS_ACCOUNT_ID: ").strip()
    )
    validate_instagram_values(resolved_access_token, resolved_business_account_id)
    payload = build_payload(
        config,
        access_token=resolved_access_token,
        business_account_id=resolved_business_account_id,
    )
    output = run_ssh(
        config,
        f"python3 -c {REMOTE_SCRIPT!r}",
        payload=payload,
    )
    print(output)
    print("INSTAGRAM_ENV_UPDATE=OK; valores nao foram exibidos")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(config_from_args(parse_args(argv)))
    except (InstagramEnvConfigError, subprocess.TimeoutExpired) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

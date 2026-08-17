from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

CONFIRMATION = "UPDATE_N8N_BOOTSTRAP_OWNER"
DEFAULT_HOST = "root@76.13.237.105"
DEFAULT_REMOTE_PATH = PurePosixPath(
    "/opt/automacao_grupo_compras/n8n/bootstrap-owner.txt"
)

REMOTE_INSPECT_COMMAND = (
    "set -Eeuo pipefail; "
    f"target='{DEFAULT_REMOTE_PATH}'; "
    "test -f \"$target\"; "
    "stat -c 'REMOTE_FILE mode=%a owner=%U group=%G bytes=%s' \"$target\""
)

REMOTE_UPDATE_COMMAND = (
    "set -Eeuo pipefail; "
    f"target='{DEFAULT_REMOTE_PATH}'; "
    "backup=\"${target}.bak\"; "
    "tmp=$(mktemp \"${target}.tmp.XXXXXX\"); "
    "trap 'rm -f \"$tmp\"' EXIT; "
    "if test -f \"$target\"; then "
    "cp -p -- \"$target\" \"$backup\"; chmod 600 \"$backup\"; "
    "fi; "
    "cat > \"$tmp\"; "
    "test -s \"$tmp\"; "
    "chown root:root \"$tmp\"; chmod 600 \"$tmp\"; "
    "mv -f -- \"$tmp\" \"$target\"; "
    "trap - EXIT; "
    "stat -c 'UPDATED mode=%a owner=%U group=%G bytes=%s' \"$target\"; "
    "test ! -f \"$backup\" || "
    "stat -c 'BACKUP mode=%a owner=%U group=%G bytes=%s' \"$backup\""
)


class BootstrapOwnerUpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateConfig:
    host: str
    identity_file: Path
    ssh_bin: Path | str
    apply: bool
    confirmation: str | None
    email: str | None


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
            "Atualiza com seguranca a credencial bootstrap do owner n8n na VPS. "
            "Sem --apply, executa somente o preflight remoto."
        )
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument(
        "--identity-file",
        type=Path,
        default=Path.home() / ".ssh/hostinger_n8n_ed25519",
    )
    parser.add_argument("--ssh-bin", type=Path, default=default_ssh_bin())
    parser.add_argument("--email")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-remote-write")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> UpdateConfig:
    return UpdateConfig(
        host=str(args.host).strip(),
        identity_file=args.identity_file.expanduser().resolve(),
        ssh_bin=args.ssh_bin,
        apply=bool(args.apply),
        confirmation=args.confirm_remote_write,
        email=str(args.email).strip() if args.email else None,
    )


def validate_config(config: UpdateConfig) -> None:
    if not config.host or any(character.isspace() for character in config.host):
        raise BootstrapOwnerUpdateError("host SSH invalido")
    if not config.identity_file.is_file():
        raise BootstrapOwnerUpdateError(
            f"chave SSH nao encontrada: {config.identity_file}"
        )
    if config.apply and config.confirmation != CONFIRMATION:
        raise BootstrapOwnerUpdateError(
            f"--confirm-remote-write deve ser exatamente {CONFIRMATION}"
        )


def validate_credentials(email: str, password: str, confirmation: str) -> None:
    if not email or "@" not in email or "\n" in email or "\r" in email:
        raise BootstrapOwnerUpdateError("email do owner n8n invalido")
    if not password or "\n" in password or "\r" in password:
        raise BootstrapOwnerUpdateError("senha do owner n8n invalida")
    if password != confirmation:
        raise BootstrapOwnerUpdateError("as senhas informadas nao conferem")


def credential_payload(email: str, password: str) -> str:
    return f"email={email}\npassword={password}\n"


def ssh_command(config: UpdateConfig, remote_command: str) -> list[str]:
    return [
        str(config.ssh_bin),
        "-i",
        str(config.identity_file),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=10",
        config.host,
        remote_command,
    ]


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
        timeout=30,
    )
    if completed.returncode != 0:
        raise BootstrapOwnerUpdateError(
            "comando SSH falhou; "
            f"codigo={completed.returncode}; stderr={completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def run(
    config: UpdateConfig,
    *,
    email: str | None = None,
    password: str | None = None,
    password_confirmation: str | None = None,
) -> int:
    validate_config(config)
    if not config.apply:
        print(run_ssh(config, REMOTE_INSPECT_COMMAND))
        print("DRY_RUN=true; nenhuma credencial foi alterada")
        return 0

    resolved_email = email or config.email or input("Email do owner n8n: ").strip()
    resolved_password = password if password is not None else getpass.getpass(
        "Senha atual do owner n8n: "
    )
    resolved_confirmation = (
        password_confirmation
        if password_confirmation is not None
        else getpass.getpass("Confirme a senha: ")
    )
    validate_credentials(resolved_email, resolved_password, resolved_confirmation)

    output = run_ssh(
        config,
        REMOTE_UPDATE_COMMAND,
        payload=credential_payload(resolved_email, resolved_password),
    )
    print(output)
    print("CREDENTIAL_UPDATE=OK; valores nao foram exibidos")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(config_from_args(parse_args(argv)))
    except (BootstrapOwnerUpdateError, subprocess.TimeoutExpired) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

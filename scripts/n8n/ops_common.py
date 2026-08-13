from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_COMPOSE_ENV = Path("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE_FILE = Path("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
DEFAULT_WORKFLOW_ID = "OfertasMvpSupab1"
DEFAULT_BOOTSTRAP_OWNER = Path("/opt/automacao_grupo_compras/n8n/bootstrap-owner.txt")
DEFAULT_N8N_BASE_URL = "https://n8n-owco.srv1805131.hstgr.cloud"

REAL_GROUP_TARGET = "grupo-ofertas-feminino"
REAL_GROUP_CHAT_ID = "120363412864266334@g.us"
TEST_PHONE_TARGET = "5511975235421"
TEST_PHONE_CHAT_ID = "5511975235421@c.us"
REAL_GROUP_LIMIT = 8
DEFAULT_SEND_DELAY_SECONDS_MIN = 45
DEFAULT_SEND_DELAY_SECONDS_MAX = 90


class N8nOpsError(RuntimeError):
    pass


@dataclass(frozen=True)
class ComposeConfig:
    compose_env: Path = DEFAULT_COMPOSE_ENV
    compose_file: Path = DEFAULT_COMPOSE_FILE


@dataclass(frozen=True)
class OperationMode:
    name: str
    pin_data: dict[str, Any] | None
    real_send: bool


def build_pin_data(
    *,
    dry_run: bool,
    target: str,
    allowed_targets_csv: str,
    target_chat_id: str | None = None,
    limit: int = 1,
    send_delay_seconds_min: int = DEFAULT_SEND_DELAY_SECONDS_MIN,
    send_delay_seconds_max: int = DEFAULT_SEND_DELAY_SECONDS_MAX,
    profile: str = "feminino",
    marketplace: str = "shopee",
    channel_adapter: str = "whatsapp",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "dry_run": dry_run,
        "limit": limit,
        "profile": profile,
        "marketplace": marketplace,
        "target": target,
        "allowed_targets_csv": allowed_targets_csv,
        "channel_adapter": channel_adapter,
        "send_delay_seconds_min": send_delay_seconds_min,
        "send_delay_seconds_max": send_delay_seconds_max,
    }
    if target_chat_id:
        payload["target_chat_id"] = target_chat_id
    return {"Trigger Manual": [{"json": payload}]}


REAL_GROUP_PINDATA = build_pin_data(
    dry_run=False,
    target=REAL_GROUP_TARGET,
    target_chat_id=REAL_GROUP_CHAT_ID,
    allowed_targets_csv=REAL_GROUP_TARGET,
    limit=REAL_GROUP_LIMIT,
)

TEST_PHONE_PINDATA = build_pin_data(
    dry_run=False,
    target=TEST_PHONE_TARGET,
    target_chat_id=TEST_PHONE_CHAT_ID,
    allowed_targets_csv=TEST_PHONE_TARGET,
)

SAFE_PINDATA = build_pin_data(
    dry_run=True,
    target="teste-whatsapp",
    allowed_targets_csv="teste-whatsapp",
)

OPERATION_MODES = {
    "grupo-real": OperationMode("grupo-real", REAL_GROUP_PINDATA, True),
    "teste-telefone": OperationMode("teste-telefone", TEST_PHONE_PINDATA, True),
    "dry-run": OperationMode("dry-run", SAFE_PINDATA, False),
    "preserve-pindata": OperationMode("preserve-pindata", None, False),
}


def resolve_mode(mode: str) -> OperationMode:
    try:
        return OPERATION_MODES[mode]
    except KeyError as exc:
        allowed = ", ".join(sorted(OPERATION_MODES))
        raise N8nOpsError(f"modo operacional invalido: {mode}. Permitidos: {allowed}") from exc


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def dollar_quote(value: str, base_tag: str = "n8njson") -> str:
    tag = base_tag
    suffix = 0
    while f"${tag}$" in value:
        suffix += 1
        tag = f"{base_tag}{suffix}"
    return f"${tag}${value}${tag}$"


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def compose_psql_command(config: ComposeConfig, *extra: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(config.compose_env),
        "-f",
        str(config.compose_file),
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "n8n",
        "-d",
        "n8n",
        "-v",
        "ON_ERROR_STOP=1",
        *extra,
    ]


def run_psql(sql: str, config: ComposeConfig) -> str:
    completed = subprocess.run(
        compose_psql_command(config),
        input=sql,
        text=True,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise N8nOpsError(
            "psql command failed:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    return completed.stdout


def fetch_psql_value(sql: str, config: ComposeConfig) -> str:
    completed = subprocess.run(
        compose_psql_command(config, "-At", "-c", sql),
        text=True,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise N8nOpsError(
            "psql query failed:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    return completed.stdout.strip()


def update_pin_data_sql(workflow_id: str, pin_data: dict[str, Any]) -> str:
    return (
        "update workflow_entity\n"
        f"set \"pinData\" = {dollar_quote(compact_json(pin_data))}::json,\n"
        "    \"updatedAt\" = now()\n"
        f"where id = {sql_literal(workflow_id)};"
    )


def decode_referenced_json(raw: str) -> Any:
    values = json.loads(raw)
    if not isinstance(values, list) or not values:
        raise N8nOpsError("execution_data.data vazio ou invalido")
    memo: dict[int, Any] = {}

    def revive(value: Any) -> Any:
        if isinstance(value, str) and value.isdigit() and int(value) < len(values):
            return revive(values[int(value)])
        object_id = id(value)
        if isinstance(value, list):
            if object_id in memo:
                return memo[object_id]
            output: list[Any] = []
            memo[object_id] = output
            output.extend(revive(item) for item in value)
            return output
        if isinstance(value, dict):
            if object_id in memo:
                return memo[object_id]
            output: dict[str, Any] = {}
            memo[object_id] = output
            output.update((key, revive(item)) for key, item in value.items())
            return output
        return value

    return revive(values[0])


def first_node_json(decoded_execution: dict[str, Any], node_name: str) -> dict[str, Any] | None:
    try:
        run_data = decoded_execution["resultData"]["runData"]
        node_runs = run_data[node_name]
        return node_runs[0]["data"]["main"][0][0]["json"]
    except (KeyError, IndexError, TypeError):
        return None


def all_first_node_json(decoded_execution: dict[str, Any]) -> dict[str, dict[str, Any]]:
    try:
        run_data = decoded_execution["resultData"]["runData"]
    except (KeyError, TypeError):
        return {}
    output: dict[str, dict[str, Any]] = {}
    for node_name in run_data:
        node_json = first_node_json(decoded_execution, node_name)
        if isinstance(node_json, dict):
            output[node_name] = node_json
    return output


def parse_bootstrap_owner(path: Path = DEFAULT_BOOTSTRAP_OWNER) -> dict[str, str]:
    if not path.is_file():
        raise N8nOpsError(f"bootstrap owner file not found: {path}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        normalized = re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")
        values[normalized] = value.strip()
    return values


def bootstrap_field(values: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in values and values[candidate]:
            return values[candidate]
    for key, value in values.items():
        if any(candidate in key for candidate in candidates) and value:
            return value
    return None

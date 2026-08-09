from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ops_common import (
    DEFAULT_BOOTSTRAP_OWNER,
    DEFAULT_COMPOSE_ENV,
    DEFAULT_COMPOSE_FILE,
    DEFAULT_N8N_BASE_URL,
    DEFAULT_WORKFLOW_ID,
    ComposeConfig,
    N8nOpsError,
    bootstrap_field,
    fetch_psql_value,
    parse_bootstrap_owner,
    resolve_mode,
    run_psql,
    sql_literal,
    update_pin_data_sql,
)


class WorkflowRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunConfig:
    mode: str
    workflow_id: str
    compose_env: Path
    compose_file: Path
    bootstrap_owner: Path
    base_url: str
    timeout_seconds: int
    poll_seconds: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the guarded n8n workflow manually through the n8n REST API."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=("grupo-real", "teste-telefone", "dry-run"),
        help="Operational mode. Required to avoid accidental real sends.",
    )
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--compose-env", type=Path, default=DEFAULT_COMPOSE_ENV)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--bootstrap-owner", type=Path, default=DEFAULT_BOOTSTRAP_OWNER)
    parser.add_argument("--base-url", default=DEFAULT_N8N_BASE_URL)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--poll-seconds", type=int, default=20)
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> RunConfig:
    return RunConfig(
        mode=args.mode,
        workflow_id=args.workflow_id,
        compose_env=args.compose_env,
        compose_file=args.compose_file,
        bootstrap_owner=args.bootstrap_owner,
        base_url=args.base_url.rstrip("/"),
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )


def latest_execution_id(workflow_id: str, compose_config: ComposeConfig) -> int:
    raw = fetch_psql_value(
        "select coalesce(max(id), 0) "
        "from execution_entity "
        f"where \"workflowId\" = {sql_literal(workflow_id)};",
        compose_config,
    )
    return int(raw or "0")


def execution_after(
    workflow_id: str,
    previous_execution_id: int,
    compose_config: ComposeConfig,
) -> int | None:
    raw = fetch_psql_value(
        "select id "
        "from execution_entity "
        f"where \"workflowId\" = {sql_literal(workflow_id)} "
        f"  and id > {previous_execution_id} "
        "order by id desc "
        "limit 1;",
        compose_config,
    )
    return int(raw) if raw else None


def wait_for_execution(
    workflow_id: str,
    previous_execution_id: int,
    compose_config: ComposeConfig,
    poll_seconds: int,
) -> int | None:
    deadline = time.monotonic() + poll_seconds
    while time.monotonic() <= deadline:
        execution_id = execution_after(workflow_id, previous_execution_id, compose_config)
        if execution_id is not None:
            return execution_id
        time.sleep(1)
    return None


def read_credentials(path: Path) -> tuple[str, str]:
    values = parse_bootstrap_owner(path)
    email = bootstrap_field(values, ("email", "user", "username", "login"))
    password = bootstrap_field(values, ("password", "senha"))
    if not email or not password:
        raise WorkflowRunError(
            f"nao foi possivel localizar email/senha em {path}; valores nao foram impressos"
        )
    return email, password


def request_json(
    opener: urllib.request.OpenerDirector,
    url: str,
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise WorkflowRunError(f"n8n HTTP {exc.code} em {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise WorkflowRunError(f"falha ao chamar n8n em {url}: {exc.reason}") from exc
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WorkflowRunError(f"n8n retornou JSON invalido em {url}") from exc
    return parsed if isinstance(parsed, dict) else {"response": parsed}


def login_opener(config: RunConfig) -> urllib.request.OpenerDirector:
    email, password = read_credentials(config.bootstrap_owner)
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    request_json(
        opener,
        f"{config.base_url}/rest/login",
        {"emailOrLdapLoginId": email, "password": password},
        config.timeout_seconds,
    )
    if not cookie_jar:
        raise WorkflowRunError("login n8n nao retornou cookie de sessao")
    return opener


def run_workflow_api(config: RunConfig, opener: urllib.request.OpenerDirector) -> dict[str, Any]:
    return request_json(
        opener,
        f"{config.base_url}/rest/workflows/{config.workflow_id}/run",
        {
            "runData": {},
            "destinationNode": {
                "nodeName": "Registrar Resultado Supabase",
                "mode": "inclusive",
            },
        },
        config.timeout_seconds,
    )


def run(config: RunConfig) -> int:
    operation_mode = resolve_mode(config.mode)
    if operation_mode.pin_data is None:
        raise WorkflowRunError("run_workflow_manual nao aceita preserve-pindata")

    compose_config = ComposeConfig(config.compose_env, config.compose_file)
    previous_execution_id = latest_execution_id(config.workflow_id, compose_config)
    run_psql(update_pin_data_sql(config.workflow_id, operation_mode.pin_data), compose_config)

    opener = login_opener(config)
    response = run_workflow_api(config, opener)
    execution_id = wait_for_execution(
        config.workflow_id,
        previous_execution_id,
        compose_config,
        config.poll_seconds,
    )

    print(f"INFO | workflow_id={config.workflow_id}")
    print(f"INFO | mode={config.mode}")
    print(f"INFO | previous_execution_id={previous_execution_id}")
    if execution_id is not None:
        print(f"INFO | execution_id={execution_id}")
    else:
        print("INFO | execution_id=not-found-after-api-call")
    if response:
        print("INFO | n8n_response=received")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(config_from_args(parse_args(argv)))
    except (WorkflowRunError, N8nOpsError) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

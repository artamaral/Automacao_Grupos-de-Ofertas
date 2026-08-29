from __future__ import annotations

import argparse
import http.cookiejar
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from ops_common import (
    DEFAULT_BOOTSTRAP_OWNER,
    DEFAULT_COMPOSE_ENV,
    DEFAULT_COMPOSE_FILE,
    DEFAULT_N8N_BASE_URL,
    ComposeConfig,
    bootstrap_field,
    compose_psql_command,
    fetch_psql_value,
    parse_bootstrap_owner,
)

WORKFLOW_ID = "OfertasMvpSupab1"
BASE = "offers.v_daily_dispatch_ready"
TRACKED = "offers.v_daily_dispatch_ready_tracked"
CONFIRMATION = "DEPLOY_SHOPEE_TRACKED_READY_VIEW"


def sql(*, rollback: bool = False) -> str:
    source = TRACKED if rollback else BASE
    target = BASE if rollback else TRACKED
    return f"""
do $$
declare source_count integer;
begin
  select (length(nodes::text)-length(replace(nodes::text,'{source}',''))) / length('{source}')
    into source_count from workflow_entity where id='{WORKFLOW_ID}';
  if source_count <> 3 then
    raise exception 'expected 3 source view references, got %', source_count;
  end if;
end $$;
with updated as (
  update workflow_entity
  set nodes=replace(nodes::text, '{source}', '{target}')::json,
      "versionId"=gen_random_uuid()::text,
      "versionCounter"=coalesce("versionCounter",0)+1,
      "updatedAt"=now()
  where id='{WORKFLOW_ID}'
  returning *
)
insert into workflow_history(
  "versionId","workflowId",authors,"createdAt","updatedAt",nodes,connections,
  name,autosaved,description,"nodeGroups"
)
select "versionId",id,coalesce((select authors from workflow_history h
  where h."workflowId"=id order by h."createdAt" desc limit 1),'system'),
  "updatedAt","updatedAt",nodes,connections,name,false,null,'[]'::json
from updated;
"""


def status_sql() -> str:
    base_text = f"replace(nodes::text, '{TRACKED}', '')"
    return f"""
select json_build_object(
  'id', id,
  'active', active,
  'versionId', "versionId",
  'activeVersionId', "activeVersionId",
  'versionCounter', "versionCounter",
  'base_refs', (length({base_text}) - length(replace({base_text}, '{BASE}', '')))
    / length('{BASE}'),
  'tracked_refs', (length(nodes::text) - length(replace(nodes::text, '{TRACKED}', '')))
    / length('{TRACKED}'),
  'pinData', "pinData"
)::text
from workflow_entity
where id='{WORKFLOW_ID}';
"""


def fetch_db_status(config: ComposeConfig) -> dict[str, Any]:
    raw = fetch_psql_value(status_sql(), config)
    if not raw:
        raise RuntimeError(f"workflow not found: {WORKFLOW_ID}")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError("workflow status is not an object")
    return value


def deployment_action(status: dict[str, Any], *, rollback: bool) -> str:
    source_refs = int(status["tracked_refs"] if rollback else status["base_refs"])
    target_refs = int(status["base_refs"] if rollback else status["tracked_refs"])
    if source_refs == 3 and target_refs == 0:
        return "update"
    if source_refs == 0 and target_refs == 3:
        return "publish"
    raise RuntimeError(
        "unexpected workflow view references: "
        f"base={status.get('base_refs')} tracked={status.get('tracked_refs')}"
    )


def run_update(config: ComposeConfig, *, rollback: bool) -> None:
    completed = subprocess.run(
        compose_psql_command(config),
        input=sql(rollback=rollback),
        text=True,
        check=False,
        capture_output=True,
    )
    if completed.returncode:
        raise RuntimeError(
            "tracked ready view deploy failed: "
            f"stdout={completed.stdout} stderr={completed.stderr}"
        )


def request_json(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    method: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"n8n HTTP {exc.code} at {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"n8n request failed at {url}: {exc.reason}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("n8n response is not an object")
    data = parsed.get("data", parsed)
    if not isinstance(data, dict):
        raise RuntimeError("n8n response data is not an object")
    return data


def authenticated_opener(
    bootstrap_owner: Path, base_url: str, timeout_seconds: int
) -> urllib.request.OpenerDirector:
    values = parse_bootstrap_owner(bootstrap_owner)
    email = bootstrap_field(values, ("email", "user", "username", "login"))
    password = bootstrap_field(values, ("password", "senha"))
    if not email or not password:
        raise RuntimeError("n8n bootstrap owner credentials not found; values were not printed")
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    request_json(
        opener,
        f"{base_url}/rest/login",
        method="POST",
        payload={"emailOrLdapLoginId": email, "password": password},
        timeout_seconds=timeout_seconds,
    )
    if not cookie_jar:
        raise RuntimeError("n8n login did not return a session cookie")
    return opener


def view_reference_counts(value: Any) -> tuple[int, int]:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    tracked_refs = text.count(TRACKED)
    base_refs = text.replace(TRACKED, "").count(BASE)
    return base_refs, tracked_refs


def validate_published_workflow(
    workflow: dict[str, Any], *, expected_version_id: str, rollback: bool
) -> None:
    expected_base = 3 if rollback else 0
    expected_tracked = 0 if rollback else 3
    active_base, active_tracked = view_reference_counts(workflow.get("activeVersion"))
    errors: list[str] = []
    if workflow.get("active") is not True:
        errors.append("workflow must remain active")
    if workflow.get("versionId") != expected_version_id:
        errors.append("workflow versionId changed during publication")
    if workflow.get("activeVersionId") != expected_version_id:
        errors.append("activeVersionId does not match the published versionId")
    if (active_base, active_tracked) != (expected_base, expected_tracked):
        errors.append(
            "activeVersion view references mismatch: "
            f"base={active_base} tracked={active_tracked}"
        )
    if errors:
        raise RuntimeError("; ".join(errors))


def publish_current_version(
    *,
    bootstrap_owner: Path,
    base_url: str,
    timeout_seconds: int,
    expected_version_id: str,
    rollback: bool,
) -> dict[str, Any]:
    opener = authenticated_opener(bootstrap_owner, base_url, timeout_seconds)
    workflow_url = f"{base_url}/rest/workflows/{WORKFLOW_ID}"
    before = request_json(opener, workflow_url, method="GET", timeout_seconds=timeout_seconds)
    if before.get("versionId") != expected_version_id:
        raise RuntimeError("n8n API versionId does not match the database draft")
    checksum = str(before.get("checksum") or "").strip()
    if not checksum:
        raise RuntimeError("n8n workflow checksum is required for publication")
    request_json(
        opener,
        f"{workflow_url}/activate",
        method="POST",
        payload={"versionId": expected_version_id, "expectedChecksum": checksum},
        timeout_seconds=timeout_seconds,
    )
    after = request_json(opener, workflow_url, method="GET", timeout_seconds=timeout_seconds)
    validate_published_workflow(
        after, expected_version_id=expected_version_id, rollback=rollback
    )
    return after


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose-env", default=str(DEFAULT_COMPOSE_ENV))
    parser.add_argument("--compose-file", default=str(DEFAULT_COMPOSE_FILE))
    parser.add_argument("--bootstrap-owner", type=Path, default=DEFAULT_BOOTSTRAP_OWNER)
    parser.add_argument("--base-url", default=DEFAULT_N8N_BASE_URL)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--confirm-remote-write")
    args = parser.parse_args()
    if not args.apply:
        print(f"dry_run=true source_references=3 rollback={args.rollback}")
        return 0
    if args.confirm_remote_write != CONFIRMATION:
        raise ValueError(f"--confirm-remote-write must be {CONFIRMATION}")

    compose = ComposeConfig(Path(args.compose_env), Path(args.compose_file))
    before = fetch_db_status(compose)
    pin_data_before = before.get("pinData")
    action = deployment_action(before, rollback=args.rollback)
    if action == "update":
        run_update(compose, rollback=args.rollback)
    draft = fetch_db_status(compose)
    if draft.get("pinData") != pin_data_before:
        raise RuntimeError("pinData changed during tracked ready view deployment")
    expected_base = 3 if args.rollback else 0
    expected_tracked = 0 if args.rollback else 3
    if (int(draft["base_refs"]), int(draft["tracked_refs"])) != (
        expected_base,
        expected_tracked,
    ):
        raise RuntimeError("database draft does not contain the expected view references")
    version_id = str(draft["versionId"])
    published = publish_current_version(
        bootstrap_owner=args.bootstrap_owner,
        base_url=args.base_url.rstrip("/"),
        timeout_seconds=args.timeout_seconds,
        expected_version_id=version_id,
        rollback=args.rollback,
    )
    print(
        f"workflow_id={WORKFLOW_ID} rollback={args.rollback} action={action} "
        f"version_id={version_id} active_version_id={published.get('activeVersionId')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

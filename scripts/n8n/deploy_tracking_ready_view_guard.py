from __future__ import annotations

import argparse
import subprocess

from ops_common import ComposeConfig, compose_psql_command

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
    into source_count from workflow_entity where id='OfertasMvpSupab1';
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
  where id='OfertasMvpSupab1'
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose-env", default="/opt/automacao_grupo_compras/n8n/.env")
    parser.add_argument(
        "--compose-file", default="/opt/automacao_grupo_compras/n8n/docker-compose.yml"
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--confirm-remote-write")
    args = parser.parse_args()
    if not args.apply:
        print(f"dry_run=true source_references=3 rollback={args.rollback}")
        return 0
    if args.confirm_remote_write != CONFIRMATION:
        raise ValueError(f"--confirm-remote-write must be {CONFIRMATION}")
    completed = subprocess.run(
        compose_psql_command(ComposeConfig(args.compose_env, args.compose_file)),
        input=sql(rollback=args.rollback), text=True, check=False,
    )
    if completed.returncode:
        raise RuntimeError("tracked ready view deploy failed")
    print(f"workflow_id=OfertasMvpSupab1 rollback={args.rollback}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

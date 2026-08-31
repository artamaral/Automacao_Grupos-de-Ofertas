from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ops_common import (
    ComposeConfig,
    N8nOpsError,
    compact_json,
    compose_psql_command,
    dollar_quote,
    sql_literal,
)

DEFAULT_WORKFLOW_JSON = Path("n8n/workflows/ofertas-instagram-supabase.json")
DEFAULT_COMPOSE_ENV = Path("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE_FILE = Path("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
DEFAULT_WORKFLOW_ID = "OfertasInstagramSupab1"
EXPECTED_WORKFLOW_TIMEZONE = "America/Sao_Paulo"
EXPECTED_TARGET = "oferta.femininas"
EXPECTED_SCHEDULE_CRON = "0 10,12,14,16,18,20 * * *"
EXPECTED_SCHEDULE_NODE = "Schedule Instagram Controlado"
EXPECTED_SCHEDULE_CONTEXT_NODE = "Set Contexto Schedule Instagram"
DEFAULT_WHATSAPP_GROUP_URL = "https://chat.whatsapp.com/FWM9EbDd0eQ7bHxr2iOf9K"
DEFAULT_INSTAGRAM_BUSINESS_ACCOUNT_ID = "__configure_instagram_business_account_id__"
EXPECTED_HTTP_HEADER_CREDENTIAL_ID = "instagramGraphHdrAuth1"
EXPECTED_HTTP_HEADER_CREDENTIAL_NAME = "Instagram Graph Bearer"


class InstagramWorkflowGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeployConfig:
    workflow_json: Path
    workflow_id: str
    compose_env: Path
    compose_file: Path
    pin_data: dict[str, Any] | None
    dry_run: bool
    mode: str = "safe"
    instagram_business_account_id: str | None = None
    whatsapp_group_url: str = DEFAULT_WHATSAPP_GROUP_URL


def build_pin_data(
    *,
    dry_run: bool,
    run_id: str,
    instagram_business_account_id: str = DEFAULT_INSTAGRAM_BUSINESS_ACCOUNT_ID,
    whatsapp_group_url: str = DEFAULT_WHATSAPP_GROUP_URL,
) -> dict[str, Any]:
    return {
        "Trigger Manual": [
            {
                "json": {
                    "dry_run": dry_run,
                    "profile": "feminino",
                    "marketplace": "shopee",
                    "target": EXPECTED_TARGET,
                    "allowed_targets_csv": EXPECTED_TARGET,
                    "limit": 1,
                    "run_id": run_id,
                    "instagram_account_email": "grupodeofertas.mktdigital.fem@gmail.com",
                    "instagram_username": EXPECTED_TARGET,
                    "instagram_business_account_id": instagram_business_account_id,
                    "whatsapp_group_url": whatsapp_group_url,
                }
            }
        ]
    }


SAFE_PINDATA = build_pin_data(dry_run=True, run_id="instagram-safe-dry-run")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and deploy the guarded Instagram n8n workflow JSON."
    )
    parser.add_argument("--workflow-json", type=Path, default=DEFAULT_WORKFLOW_JSON)
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--compose-env", type=Path, default=DEFAULT_COMPOSE_ENV)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mode",
        choices=(
            "safe",
            "instagram-real-test",
            "instagram-production",
            "preserve-pindata",
        ),
        default="safe",
    )
    return parser.parse_args(argv)


def read_operational_env(compose_env: Path) -> dict[str, str]:
    if not compose_env.is_file():
        raise InstagramWorkflowGuardError(f"compose env not found: {compose_env}")
    values: dict[str, str] = {}
    for raw_line in compose_env.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def read_real_instagram_settings(compose_env: Path, mode: str) -> tuple[str, str]:
    env_values = read_operational_env(compose_env)
    instagram_business_account_id = env_values.get(
        "INSTAGRAM_BUSINESS_ACCOUNT_ID", ""
    ).strip()
    whatsapp_group_url = (
        env_values.get("INSTAGRAM_WHATSAPP_GROUP_URL", "").strip()
        or DEFAULT_WHATSAPP_GROUP_URL
    )
    if not instagram_business_account_id:
        raise InstagramWorkflowGuardError(
            f"INSTAGRAM_BUSINESS_ACCOUNT_ID ausente no compose env para {mode}"
        )
    if whatsapp_group_url != DEFAULT_WHATSAPP_GROUP_URL:
        raise InstagramWorkflowGuardError(
            "INSTAGRAM_WHATSAPP_GROUP_URL deve corresponder ao grupo publico versionado"
        )
    return instagram_business_account_id, whatsapp_group_url


def config_from_args(args: argparse.Namespace) -> DeployConfig:
    compose_env = args.compose_env
    pin_data: dict[str, Any] | None
    instagram_business_account_id: str | None = None
    whatsapp_group_url = DEFAULT_WHATSAPP_GROUP_URL

    if args.mode == "safe":
        pin_data = SAFE_PINDATA
    elif args.mode in {"instagram-real-test", "instagram-production"}:
        instagram_business_account_id, whatsapp_group_url = read_real_instagram_settings(
            compose_env, args.mode
        )
        run_id = (
            "instagram-real-test"
            if args.mode == "instagram-real-test"
            else "instagram-production-manual"
        )
        pin_data = build_pin_data(
            dry_run=False,
            run_id=run_id,
            instagram_business_account_id=instagram_business_account_id,
            whatsapp_group_url=whatsapp_group_url,
        )
    else:
        pin_data = None

    return DeployConfig(
        workflow_json=args.workflow_json,
        workflow_id=args.workflow_id,
        compose_env=compose_env,
        compose_file=args.compose_file,
        pin_data=pin_data,
        dry_run=args.dry_run,
        mode=args.mode,
        instagram_business_account_id=instagram_business_account_id,
        whatsapp_group_url=whatsapp_group_url,
    )


def load_workflow(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InstagramWorkflowGuardError(f"workflow JSON not found: {path}")
    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InstagramWorkflowGuardError(f"invalid workflow JSON: {path}: {exc}") from exc
    if not isinstance(workflow, dict):
        raise InstagramWorkflowGuardError("workflow JSON must be an object")
    return workflow


def workflow_text(workflow: dict[str, Any]) -> str:
    return json.dumps(workflow, ensure_ascii=False, sort_keys=True)


def node_by_name(workflow: dict[str, Any], name: str) -> dict[str, Any] | None:
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        return None
    for node in nodes:
        if isinstance(node, dict) and node.get("name") == name:
            return node
    return None


def _targets(connections: dict[str, Any], name: str) -> list[set[str | None]]:
    outputs = connections.get(name, {}).get("main", [])
    return [
        {target.get("node") for target in output if isinstance(target, dict)}
        for output in outputs
        if isinstance(output, list)
    ]


def _schedule_cron(workflow: dict[str, Any]) -> str:
    node = node_by_name(workflow, EXPECTED_SCHEDULE_NODE)
    if not isinstance(node, dict):
        return ""
    intervals = node.get("parameters", {}).get("rule", {}).get("interval", [])
    if not isinstance(intervals, list):
        return ""
    for interval in intervals:
        if isinstance(interval, dict) and interval.get("field") == "cronExpression":
            return str(interval.get("expression") or "")
    return ""


def _schedule_context_code(workflow: dict[str, Any]) -> str:
    node = node_by_name(workflow, EXPECTED_SCHEDULE_CONTEXT_NODE)
    if not isinstance(node, dict):
        return ""
    return str(node.get("parameters", {}).get("jsCode", ""))


def build_production_schedule_context(
    *, instagram_business_account_id: str, whatsapp_group_url: str
) -> str:
    if not instagram_business_account_id.strip():
        raise InstagramWorkflowGuardError(
            "instagram business account id obrigatorio para schedule de producao"
        )
    if whatsapp_group_url != DEFAULT_WHATSAPP_GROUP_URL:
        raise InstagramWorkflowGuardError(
            "whatsapp group url deve corresponder ao grupo publico versionado"
        )
    return (
        "return [{ json: { "
        "dry_run: false, "
        "profile: 'feminino', "
        "marketplace: 'shopee', "
        "target: 'oferta.femininas', "
        "allowed_targets_csv: 'oferta.femininas', "
        "limit: 1, "
        "run_id: new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '-instagram-schedule', "
        "instagram_account_email: 'grupodeofertas.mktdigital.fem@gmail.com', "
        "instagram_username: 'oferta.femininas', "
        f"instagram_business_account_id: '{instagram_business_account_id}', "
        f"whatsapp_group_url: '{whatsapp_group_url}' "
        "} }];"
    )


def prepare_workflow_for_deploy(
    workflow: dict[str, Any], config: DeployConfig
) -> dict[str, Any]:
    prepared = json.loads(json.dumps(workflow, ensure_ascii=False))
    if config.mode != "instagram-production":
        return prepared

    if not config.instagram_business_account_id:
        raise InstagramWorkflowGuardError(
            "instagram-production requer INSTAGRAM_BUSINESS_ACCOUNT_ID"
        )
    schedule_node = node_by_name(prepared, EXPECTED_SCHEDULE_CONTEXT_NODE)
    if not isinstance(schedule_node, dict):
        raise InstagramWorkflowGuardError(
            f"missing node: {EXPECTED_SCHEDULE_CONTEXT_NODE}"
        )
    schedule_node.setdefault("parameters", {})["jsCode"] = build_production_schedule_context(
        instagram_business_account_id=config.instagram_business_account_id,
        whatsapp_group_url=config.whatsapp_group_url,
    )
    return prepared


def validate_versioned_workflow(workflow: dict[str, Any], workflow_id: str) -> None:
    errors: list[str] = []
    if workflow.get("id") != workflow_id:
        errors.append(f"workflow id mismatch: expected {workflow_id}, got {workflow.get('id')}")
    if workflow.get("active") is not False:
        errors.append("workflow active must be false")
    if not isinstance(workflow.get("nodes"), list):
        errors.append("workflow nodes must be a list")
    if not isinstance(workflow.get("connections"), dict):
        errors.append("workflow connections must be an object")
    if workflow.get("settings", {}).get("timezone") != EXPECTED_WORKFLOW_TIMEZONE:
        errors.append(f"workflow timezone must be {EXPECTED_WORKFLOW_TIMEZONE}")

    required_nodes = (
        "Trigger Manual",
        EXPECTED_SCHEDULE_NODE,
        EXPECTED_SCHEDULE_CONTEXT_NODE,
        "Validar Contexto Instagram",
        "Claim Item Instagram",
        "Montar Copy Instagram",
        "Revalidar Midia",
        "Dry Run Instagram?",
        "Roteador Formato",
        "Criar Container Reels",
        "Preparar Filhos Carrossel",
        "Criar Filhos Carrossel",
        "Montar Payload Pai Carrossel",
        "Criar Container Pai Carrossel",
        "Normalizar Container Criado",
        "Checar Status Container",
        "Restaurar Contexto Publicacao",
        "Container Pronto?",
        "Pode Repetir Poll Container?",
        "Aguardar Container Instagram",
        "Falhar Container Nao Pronto",
        "Publicar Container",
        "Restaurar Contexto Resultado Publicacao",
        "Marcar Midia Expirada",
        "Registrar Resultado Supabase",
    )
    for node_name in required_nodes:
        if node_by_name(workflow, node_name) is None:
            errors.append(f"missing node: {node_name}")

    cron = _schedule_cron(workflow)
    if cron != EXPECTED_SCHEDULE_CRON:
        errors.append(
            f"Instagram schedule cron must be {EXPECTED_SCHEDULE_CRON}, got {cron or '<missing>'}"
        )

    schedule_code = _schedule_context_code(workflow)
    for required_schedule_text in (
        "dry_run: true",
        "run_id: 'instagram-schedule-safe'",
        DEFAULT_INSTAGRAM_BUSINESS_ACCOUNT_ID,
        DEFAULT_WHATSAPP_GROUP_URL,
    ):
        if required_schedule_text not in schedule_code:
            errors.append(
                f"versioned schedule must remain safe; missing {required_schedule_text}"
            )
    if "dry_run: false" in schedule_code:
        errors.append("versioned schedule must not enable real publication")

    for node in workflow.get("nodes") or []:
        if not isinstance(node, dict) or node.get("type") != "n8n-nodes-base.postgres":
            continue
        credentials = node.get("credentials", {}).get("postgres")
        if not isinstance(credentials, dict):
            errors.append(f"missing postgres credentials: {node.get('name')}")
            continue
        if not credentials.get("id") or not credentials.get("name"):
            errors.append(f"incomplete postgres credentials: {node.get('name')}")

    for node_name in (
        "Criar Container Reels",
        "Criar Filhos Carrossel",
        "Criar Container Pai Carrossel",
        "Checar Status Container",
        "Publicar Container",
    ):
        node = node_by_name(workflow, node_name)
        if not isinstance(node, dict):
            continue
        credentials = node.get("credentials", {}).get("httpHeaderAuth")
        if not isinstance(credentials, dict):
            errors.append(f"missing httpHeaderAuth credentials: {node_name}")
            continue
        if credentials.get("id") != EXPECTED_HTTP_HEADER_CREDENTIAL_ID:
            errors.append(f"httpHeaderAuth id mismatch: {node_name}")
        if credentials.get("name") != EXPECTED_HTTP_HEADER_CREDENTIAL_NAME:
            errors.append(f"httpHeaderAuth name mismatch: {node_name}")

    connections = workflow.get("connections") if isinstance(workflow.get("connections"), dict) else {}
    if _targets(connections, EXPECTED_SCHEDULE_NODE) != [{EXPECTED_SCHEDULE_CONTEXT_NODE}]:
        errors.append("Schedule Instagram Controlado must connect to Set Contexto Schedule Instagram")
    if _targets(connections, EXPECTED_SCHEDULE_CONTEXT_NODE) != [{"Validar Contexto Instagram"}]:
        errors.append("Set Contexto Schedule Instagram must connect to Validar Contexto Instagram")
    if _targets(connections, "Revalidar Midia") != [{"Criar Container Reels"}]:
        errors.append("Revalidar Midia must only connect to Criar Container Reels")
    if _targets(connections, "Montar Copy Instagram") != [{"Dry Run Instagram?"}]:
        errors.append("Montar Copy Instagram must only connect to Dry Run Instagram?")
    if _targets(connections, "Checar Status Container") != [{"Restaurar Contexto Publicacao"}]:
        errors.append("Checar Status Container must only connect to Restaurar Contexto Publicacao")
    if _targets(connections, "Restaurar Contexto Publicacao") != [{"Container Pronto?"}]:
        errors.append("Restaurar Contexto Publicacao must only connect to Container Pronto?")
    if _targets(connections, "Publicar Container") != [{"Restaurar Contexto Resultado Publicacao"}]:
        errors.append("Publicar Container must only connect to Restaurar Contexto Resultado Publicacao")
    if _targets(connections, "Restaurar Contexto Resultado Publicacao") != [{"Registrar Resultado Supabase"}]:
        errors.append("Restaurar Contexto Resultado Publicacao must only connect to Registrar Resultado Supabase")

    ready_targets = _targets(connections, "Container Pronto?")
    if len(ready_targets) < 2:
        errors.append("Container Pronto? must have true and false branches")
    else:
        if "Publicar Container" not in ready_targets[0]:
            errors.append("Container Pronto? true branch must publish container")
        if "Pode Repetir Poll Container?" not in ready_targets[1]:
            errors.append("Container Pronto? false branch must evaluate poll retry")

    retry_targets = _targets(connections, "Pode Repetir Poll Container?")
    if len(retry_targets) < 2:
        errors.append("Pode Repetir Poll Container? must have true and false branches")
    else:
        if "Aguardar Container Instagram" not in retry_targets[0]:
            errors.append("Pode Repetir Poll Container? true branch must wait before retry")
        if "Falhar Container Nao Pronto" not in retry_targets[1]:
            errors.append("Pode Repetir Poll Container? false branch must register failure")

    if _targets(connections, "Aguardar Container Instagram") != [{"Checar Status Container"}]:
        errors.append("Aguardar Container Instagram must only connect to Checar Status Container")
    if _targets(connections, "Falhar Container Nao Pronto") != [{"Registrar Resultado Supabase"}]:
        errors.append("Falhar Container Nao Pronto must only connect to Registrar Resultado Supabase")

    dry_run_targets = _targets(connections, "Dry Run Instagram?")
    if len(dry_run_targets) < 2:
        errors.append("Dry Run Instagram? must have true and false branches")
    else:
        if "Registrar Resultado Supabase" not in dry_run_targets[0]:
            errors.append("dry-run true branch must register result")
        if dry_run_targets[1] != {"Revalidar Midia"}:
            errors.append("dry-run false branch must publish only through Reels media validation")

    for carousel_source in (
        "Roteador Formato",
        "Preparar Filhos Carrossel",
        "Criar Filhos Carrossel",
        "Montar Payload Pai Carrossel",
        "Criar Container Pai Carrossel",
    ):
        if _targets(connections, carousel_source):
            errors.append(f"daily Instagram flow must not use carousel node: {carousel_source}")

    claim_node = node_by_name(workflow, "Claim Item Instagram")
    claim_query = ""
    if isinstance(claim_node, dict):
        claim_query = str(claim_node.get("parameters", {}).get("query", ""))

    for required_text in (
        "offers.daily_dispatch_plan",
        "offers.offer_media_assets",
        "offers.catalog_items",
        "offers.offer_snapshots",
        "for update of plan skip locked",
        "expected.instagram_format",
        "plan.planned_date = (now() at time zone 'America/Sao_Paulo')::date",
        "media.video_url is not null",
        "instagram_confirmed < 6",
        "event.payload ->> 'source_dispatch_plan_id'",
        "event.payload ->> 'dry_run' = 'false'",
        "ctx.dry_run",
        "ctx.instagram_business_account_id",
        "ctx.whatsapp_group_url",
    ):
        if required_text not in claim_query:
            errors.append(f"missing claim contract text: {required_text}")

    for forbidden_claim_text in (
        "offers.v_instagram_dispatch_ready",
        "offers.v_offer_ranking_current",
        "dispatch_status = 'planned'",
        "is_ready_for_dispatch",
        "jsonb_array_length(media.image_urls)",
        "then 'carousel'",
        "carousel_confirmed",
    ):
        if forbidden_claim_text in claim_query:
            errors.append(f"forbidden expensive/cross-channel claim text: {forbidden_claim_text}")

    text = workflow_text(workflow)
    for required_text in (
        "nullif",
        "source_dispatch_plan_id",
        "null::uuid",
        "status = 'stale'",
        "media_revalidation_failed",
        "insert into offers.publication_events",
        "channel_adapter",
        "instagram_reels",
        "instagram_carousel",
        "delivery_status",
        "genericCredentialType",
        "httpHeaderAuth",
        EXPECTED_HTTP_HEADER_CREDENTIAL_ID,
        EXPECTED_HTTP_HEADER_CREDENTIAL_NAME,
        "Quer receber mais ofertas assim?",
        "Entre no grupo do WhatsApp",
        "Copie o link da oferta",
        "graph.instagram.com",
        "instagram_confirmed",
        "reels_requires_video_url",
        "instagram container creation id ausente",
        "item.creation_id || item.id",
        "container_status",
        "instagram_graph_container_id",
        "poll_attempt",
        "container_not_ready_timeout",
        "resume\": \"timeInterval",
        "media_type=REELS",
        "/media_publish",
        "instagram media publish id ausente",
        "instagram_media_id",
        "published_media_id",
    ):
        if required_text not in text:
            errors.append(f"missing workflow contract text: {required_text}")

    for forbidden_text in (
        "/api/sendImage",
        "/api/sendText",
        "WAHA",
        "graph.facebook.com",
        "process.env",
        "target_chat_id",
        "120363412864266334",
    ):
        if forbidden_text in text:
            errors.append(f"forbidden WhatsApp/WAHA text found: {forbidden_text}")

    if errors:
        raise InstagramWorkflowGuardError("; ".join(errors))


def validate_deploy_workflow(workflow: dict[str, Any], config: DeployConfig) -> None:
    if _schedule_cron(workflow) != EXPECTED_SCHEDULE_CRON:
        raise InstagramWorkflowGuardError("deployed workflow schedule cron mismatch")

    schedule_code = _schedule_context_code(workflow)
    if config.mode == "instagram-production":
        required = (
            "dry_run: false",
            "'-instagram-schedule'",
            config.instagram_business_account_id or "",
            config.whatsapp_group_url,
        )
        for text in required:
            if not text or text not in schedule_code:
                raise InstagramWorkflowGuardError(
                    f"instagram-production schedule context missing: {text or 'business account id'}"
                )
        if DEFAULT_INSTAGRAM_BUSINESS_ACCOUNT_ID in schedule_code:
            raise InstagramWorkflowGuardError(
                "instagram-production schedule still contains business account placeholder"
            )
        if "dry_run: true" in schedule_code:
            raise InstagramWorkflowGuardError(
                "instagram-production schedule must use dry_run=false"
            )
    else:
        if "dry_run: true" not in schedule_code:
            raise InstagramWorkflowGuardError(
                "non-production deploy must preserve safe schedule dry_run=true"
            )
        if DEFAULT_INSTAGRAM_BUSINESS_ACCOUNT_ID not in schedule_code:
            raise InstagramWorkflowGuardError(
                "non-production deploy must preserve schedule business account placeholder"
            )


def validate_pin_data(pin_data: dict[str, Any] | None) -> None:
    if pin_data is None:
        return
    try:
        payload = pin_data["Trigger Manual"][0]["json"]
    except (KeyError, IndexError, TypeError) as exc:
        raise InstagramWorkflowGuardError("pinData must contain Trigger Manual[0].json") from exc
    if not isinstance(payload.get("dry_run"), bool):
        raise InstagramWorkflowGuardError("pinData dry_run must be boolean")
    if payload.get("target") != EXPECTED_TARGET:
        raise InstagramWorkflowGuardError(f"pinData target must be {EXPECTED_TARGET}")
    allowed_targets = str(payload.get("allowed_targets_csv", "")).split(",")
    if EXPECTED_TARGET not in {target.strip() for target in allowed_targets}:
        raise InstagramWorkflowGuardError("pinData target must be allowlisted")
    if not str(payload.get("instagram_business_account_id", "")).strip():
        raise InstagramWorkflowGuardError("pinData instagram_business_account_id must be set")
    if payload.get("whatsapp_group_url") != DEFAULT_WHATSAPP_GROUP_URL:
        raise InstagramWorkflowGuardError("pinData whatsapp_group_url must match public MVP URL")


def build_update_sql(workflow: dict[str, Any], workflow_id: str, pin_data: dict[str, Any] | None) -> str:
    required_fields = ("nodes", "connections")
    missing = [field for field in required_fields if field not in workflow]
    if missing:
        raise InstagramWorkflowGuardError(f"workflow missing required fields: {missing}")
    assignments = [
        f"nodes = {dollar_quote(compact_json(workflow['nodes']))}::json",
        f"connections = {dollar_quote(compact_json(workflow['connections']))}::json",
        f"settings = {dollar_quote(compact_json(workflow.get('settings', {})))}::json",
        "active = false",
        '"versionId" = gen_random_uuid()::text',
        '"versionCounter" = coalesce(workflow_entity."versionCounter", 0) + 1',
        '"updatedAt" = now()',
    ]
    if pin_data is not None:
        assignments.insert(3, f'"pinData" = {dollar_quote(compact_json(pin_data))}::json')
    insert_columns = ["id", "name", "active", "nodes", "connections", "settings", '"pinData"', '"versionId"', '"versionCounter"', '"nodeGroups"']
    insert_values = [
        sql_literal(workflow_id),
        sql_literal(str(workflow.get("name") or workflow_id)),
        "false",
        f"{dollar_quote(compact_json(workflow['nodes']))}::json",
        f"{dollar_quote(compact_json(workflow['connections']))}::json",
        f"{dollar_quote(compact_json(workflow.get('settings', {})))}::json",
        f"{dollar_quote(compact_json(pin_data))}::json" if pin_data is not None else f"{dollar_quote(compact_json(workflow.get('pinData', {})))}::json",
        "gen_random_uuid()::text",
        "1",
        "'[]'::json",
    ]
    return (
        "with upserted_workflow as (\n"
        "  insert into workflow_entity (\n"
        f"    {', '.join(insert_columns)}\n"
        "  )\n"
        f"  values ({', '.join(insert_values)})\n"
        "  on conflict (id)\n"
        "  do update\n"
        f"  set {', '.join(assignments)}\n"
        '  returning id, "versionId", name, nodes, connections, "updatedAt"\n'
        "), shared_project as (\n"
        '  select shared."projectId"\n'
        "  from shared_workflow shared\n"
        '  order by shared."updatedAt" desc\n'
        "  limit 1\n"
        "), inserted_share as (\n"
        '  insert into shared_workflow ("workflowId", "projectId", role)\n'
        '  select upserted.id, shared_project."projectId", \'workflow:owner\'\n'
        "  from upserted_workflow upserted\n"
        "  cross join shared_project\n"
        '  on conflict ("workflowId", "projectId") do nothing\n'
        '  returning "workflowId"\n'
        ")\n"
        "insert into workflow_history (\n"
        '  "versionId", "workflowId", authors, "createdAt", "updatedAt",\n'
        '  nodes, connections, name, autosaved, description, "nodeGroups"\n'
        ")\n"
        "select\n"
        '  upserted."versionId", upserted.id,\n'
        "  coalesce((select history.authors from workflow_history history where history.\"workflowId\" = upserted.id order by history.\"createdAt\" desc limit 1), 'system'),\n"
        '  upserted."updatedAt", upserted."updatedAt", upserted.nodes,\n'
        "  upserted.connections, upserted.name, false, null, '[]'::json\n"
        "from upserted_workflow upserted;"
    )


def build_status_query(workflow_id: str) -> str:
    return (
        "select json_build_object("
        "'id', id, "
        "'active', active, "
        "'versionId', \"versionId\", "
        "'activeVersionId', \"activeVersionId\", "
        "'versionCounter', \"versionCounter\", "
        "'updatedAt', \"updatedAt\", "
        "'has_expected_schedule_cron', position('0 10,12,14,16,18,20 * * *' in nodes::text) > 0, "
        "'schedule_dry_run_false', position('dry_run: false' in nodes::text) > 0, "
        "'schedule_has_placeholder', position('__configure_instagram_business_account_id__' in nodes::text) > 0, "
        "'has_daily_plan_claim', position('offers.daily_dispatch_plan' in nodes::text) > 0, "
        "'has_expensive_ranking_claim', position('offers.v_offer_ranking_current' in nodes::text) > 0 or position('offers.v_instagram_dispatch_ready' in nodes::text) > 0, "
        "'has_publish_context_restore', position('Restaurar Contexto Resultado Publicacao' in nodes::text) > 0, "
        "'has_media_publish', position('/media_publish' in nodes::text) > 0, "
        "'has_waha', position('WAHA' in nodes::text) > 0, "
        "'history_exists', exists (select 1 from workflow_history history where history.\"workflowId\" = workflow_entity.id and history.\"versionId\" = workflow_entity.\"versionId\"), "
        "'pinData', \"pinData\""
        ")::text from workflow_entity "
        f"where id = {sql_literal(workflow_id)};"
    )


def run_update(sql: str, config: DeployConfig) -> None:
    completed = subprocess.run(
        compose_psql_command(ComposeConfig(config.compose_env, config.compose_file)),
        input=sql,
        text=True,
        encoding="utf-8",
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise InstagramWorkflowGuardError(
            "failed to update n8n workflow:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )


def fetch_status(config: DeployConfig) -> dict[str, Any]:
    completed = subprocess.run(
        compose_psql_command(
            ComposeConfig(config.compose_env, config.compose_file),
            "-At",
            "-c",
            build_status_query(config.workflow_id),
        ),
        text=True,
        encoding="utf-8",
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise InstagramWorkflowGuardError(
            "failed to fetch n8n workflow status:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    output = completed.stdout.strip()
    if not output:
        raise InstagramWorkflowGuardError(f"workflow not found in n8n: {config.workflow_id}")
    status = json.loads(output)
    if not isinstance(status, dict):
        raise InstagramWorkflowGuardError("status query did not return an object")
    return status


def validate_deployed_status(
    status: dict[str, Any], pin_data: dict[str, Any] | None, *, production: bool = False
) -> None:
    errors: list[str] = []
    if status.get("active") is not False:
        errors.append("active must be false until the deployed draft is explicitly published")
    if status.get("has_expected_schedule_cron") is not True:
        errors.append("six-slot Instagram schedule cron must be present")
    if production:
        if status.get("schedule_dry_run_false") is not True:
            errors.append("production schedule must use dry_run=false")
        if status.get("schedule_has_placeholder") is not False:
            errors.append("production schedule must not contain business account placeholder")
    else:
        if status.get("schedule_dry_run_false") is not False:
            errors.append("non-production schedule must remain dry-run")
        if status.get("schedule_has_placeholder") is not True:
            errors.append("non-production schedule must retain business account placeholder")
    if status.get("has_daily_plan_claim") is not True:
        errors.append("daily plan claim must be present")
    if status.get("has_expensive_ranking_claim") is not False:
        errors.append("expensive ranking view must be absent from claim")
    if status.get("has_publish_context_restore") is not True:
        errors.append("publish context restore must be present")
    if status.get("has_media_publish") is not True:
        errors.append("media_publish must be present")
    if status.get("has_waha") is not False:
        errors.append("WAHA must be absent")
    if status.get("history_exists") is not True:
        errors.append("current version must exist in workflow_history")
    if pin_data is not None and status.get("pinData") != pin_data:
        errors.append("deployed pinData does not match requested pinData")
    if errors:
        raise InstagramWorkflowGuardError("; ".join(errors))


def print_summary(status: dict[str, Any] | None, config: DeployConfig) -> None:
    pin_mode = "preserve"
    if config.pin_data == SAFE_PINDATA:
        pin_mode = "safe"
    elif config.mode == "instagram-real-test":
        pin_mode = "instagram-real-test"
    elif config.mode == "instagram-production":
        pin_mode = "instagram-production"

    if status is None:
        print("INFO | dry_run=true; no changes applied")
        print(f"INFO | mode={config.mode}")
        print(f"INFO | pinData mode={pin_mode}")
        print(f"INFO | schedule_cron={EXPECTED_SCHEDULE_CRON}")
        print(
            "INFO | schedule_publication="
            + ("real" if config.mode == "instagram-production" else "safe")
        )
        print("INFO | instagram workflow=ok")
        print("INFO | active=false")
        return

    print(f"INFO | workflow_id={status.get('id')}")
    print(f"INFO | versionId={status.get('versionId')}")
    print(f"INFO | activeVersionId={status.get('activeVersionId')}")
    print(f"INFO | versionCounter={status.get('versionCounter')}")
    print(f"INFO | active={str(status.get('active')).lower()}")
    print(f"INFO | mode={config.mode}")
    print(f"INFO | pinData={pin_mode}")
    print(f"INFO | schedule_cron={EXPECTED_SCHEDULE_CRON}")
    print(
        "INFO | schedule_publication="
        + ("real" if config.mode == "instagram-production" else "safe")
    )


def run(config: DeployConfig) -> int:
    versioned_workflow = load_workflow(config.workflow_json)
    validate_versioned_workflow(versioned_workflow, config.workflow_id)
    workflow = prepare_workflow_for_deploy(versioned_workflow, config)
    validate_deploy_workflow(workflow, config)
    validate_pin_data(config.pin_data)
    sql = build_update_sql(workflow, config.workflow_id, config.pin_data)
    if config.dry_run:
        print_summary(None, config)
        print(f"INFO | sql_bytes={len(sql.encode('utf-8'))}")
        return 0
    run_update(sql, config)
    status = fetch_status(config)
    validate_deployed_status(
        status,
        config.pin_data,
        production=config.mode == "instagram-production",
    )
    print_summary(status, config)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(config_from_args(parse_args(argv)))
    except (InstagramWorkflowGuardError, N8nOpsError, json.JSONDecodeError) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

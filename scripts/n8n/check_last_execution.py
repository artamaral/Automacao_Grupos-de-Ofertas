from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ops_common import (
    DEFAULT_COMPOSE_ENV,
    DEFAULT_COMPOSE_FILE,
    DEFAULT_WORKFLOW_ID,
    ComposeConfig,
    N8nOpsError,
    all_first_node_json,
    decode_referenced_json,
    fetch_psql_value,
    sql_literal,
)

NEW_TEMPLATE_MARKER = "Resgate o cupom desta p\u00e1gina"
OLD_TEMPLATE_MARKER = "Aviso: este link pode gerar comissao de afiliado"


class LastExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class CheckConfig:
    workflow_id: str
    compose_env: Path
    compose_file: Path
    execution_id: int | None
    expect_real_image: bool
    copy_chars: int


@dataclass(frozen=True)
class ExecutionSummary:
    execution_id: int
    status: str | None
    mode: str | None
    started_at: str | None
    stopped_at: str | None
    workflow_version_id: str | None
    endpoint: str
    publish_id: str | None
    delivery_status: str | None
    send_result: str | None
    adapter_response_type: str | None
    adapter_status: str | None
    product_name: str | None
    target: str | None
    image_url: str | None
    copy_template: str
    copy_excerpt: str | None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect the latest n8n workflow execution and validate the send path."
    )
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--compose-env", type=Path, default=DEFAULT_COMPOSE_ENV)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--execution-id", type=int)
    parser.add_argument(
        "--expect-real-image",
        action="store_true",
        help="Fail unless the execution used sendImage, returned image adapter type and confirmed.",
    )
    parser.add_argument("--copy-chars", type=int, default=320)
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> CheckConfig:
    return CheckConfig(
        workflow_id=args.workflow_id,
        compose_env=args.compose_env,
        compose_file=args.compose_file,
        execution_id=args.execution_id,
        expect_real_image=args.expect_real_image,
        copy_chars=args.copy_chars,
    )


def build_execution_query(config: CheckConfig) -> str:
    if config.execution_id is None:
        where = f"e.\"workflowId\" = {sql_literal(config.workflow_id)}"
    else:
        where = f"e.id = {config.execution_id}"
    return (
        "select json_build_object("
        "'id', e.id, "
        "'status', e.status, "
        "'mode', e.mode, "
        "'startedAt', e.\"startedAt\", "
        "'stoppedAt', e.\"stoppedAt\", "
        "'workflowVersionId', coalesce(d.\"workflowVersionId\", e.\"workflowVersionId\"), "
        "'workflowData', d.\"workflowData\", "
        "'data', d.data"
        ")::text "
        "from execution_entity e "
        "join execution_data d on d.\"executionId\" = e.id "
        f"where {where} "
        "order by e.id desc "
        "limit 1;"
    )


def fetch_execution(config: CheckConfig) -> dict[str, Any]:
    raw = fetch_psql_value(
        build_execution_query(config),
        ComposeConfig(config.compose_env, config.compose_file),
    )
    if not raw:
        raise LastExecutionError("nenhuma execucao encontrada")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LastExecutionError(f"psql retornou JSON invalido: {raw}") from exc
    if not isinstance(payload, dict):
        raise LastExecutionError("consulta de execucao nao retornou objeto")
    return payload


def detect_endpoint(workflow_data: Any) -> str:
    workflow_text = json.dumps(workflow_data, ensure_ascii=False)
    has_send_image = "/api/sendImage" in workflow_text
    has_send_text = "/api/sendText" in workflow_text
    if has_send_image and has_send_text:
        return "mixed"
    if has_send_image:
        return "sendImage"
    if has_send_text:
        return "sendText"
    return "unknown"


def first_present(nodes: dict[str, dict[str, Any]], field: str) -> Any:
    priority = (
        "Normalizar Resultado WAHA",
        "Montar Upsert Publication Event",
        "Preparar Envio WAHA",
        "Montar Mensagens",
        "Registrar Resultado Supabase",
    )
    for node_name in priority:
        value = nodes.get(node_name, {}).get(field)
        if value not in (None, ""):
            return value
    for node_payload in nodes.values():
        value = node_payload.get(field)
        if value not in (None, ""):
            return value
    return None


def publish_id(nodes: dict[str, dict[str, Any]]) -> str | None:
    result = nodes.get("Registrar Resultado Supabase", {}).get("publish_id")
    return str(result) if result else None


def classify_copy(message_text: str | None) -> str:
    if not message_text:
        return "missing"
    if NEW_TEMPLATE_MARKER in message_text:
        return "novo"
    if OLD_TEMPLATE_MARKER in message_text:
        return "antigo"
    return "unknown"


def build_summary(payload: dict[str, Any], copy_chars: int) -> ExecutionSummary:
    decoded = decode_referenced_json(str(payload.get("data", "")))
    if not isinstance(decoded, dict):
        raise LastExecutionError("execution_data.data decodificado nao e objeto")
    nodes = all_first_node_json(decoded)
    message_text = first_present(nodes, "message_text")
    copy_excerpt = None
    if message_text:
        copy_excerpt = " ".join(str(message_text).split())[:copy_chars]
    return ExecutionSummary(
        execution_id=int(payload["id"]),
        status=payload.get("status"),
        mode=payload.get("mode"),
        started_at=payload.get("startedAt"),
        stopped_at=payload.get("stoppedAt"),
        workflow_version_id=payload.get("workflowVersionId"),
        endpoint=detect_endpoint(payload.get("workflowData")),
        publish_id=publish_id(nodes),
        delivery_status=first_present(nodes, "delivery_status"),
        send_result=first_present(nodes, "send_result"),
        adapter_response_type=first_present(nodes, "adapter_response_type"),
        adapter_status=first_present(nodes, "adapter_status"),
        product_name=first_present(nodes, "product_name"),
        target=first_present(nodes, "target"),
        image_url=first_present(nodes, "image_url"),
        copy_template=classify_copy(str(message_text) if message_text else None),
        copy_excerpt=copy_excerpt,
    )


def validate_summary(summary: ExecutionSummary, expect_real_image: bool) -> None:
    errors: list[str] = []
    if summary.endpoint == "sendText":
        errors.append("endpoint antigo detectado: sendText")
    if summary.copy_template == "antigo":
        errors.append("copy antiga detectada")
    if expect_real_image:
        if summary.status != "success":
            errors.append(f"status esperado success, recebido {summary.status}")
        if summary.endpoint != "sendImage":
            errors.append(f"endpoint esperado sendImage, recebido {summary.endpoint}")
        if summary.delivery_status != "confirmed":
            errors.append(
                f"delivery_status esperado confirmed, recebido {summary.delivery_status}"
            )
        if summary.adapter_response_type != "image":
            errors.append(
                "adapter_response_type esperado image, "
                f"recebido {summary.adapter_response_type}"
            )
        if not summary.publish_id:
            errors.append("publish_id ausente")
        if summary.copy_template != "novo":
            errors.append(f"copy_template esperado novo, recebido {summary.copy_template}")
    if errors:
        raise LastExecutionError("; ".join(errors))


def print_summary(summary: ExecutionSummary) -> None:
    lines = {
        "execution_id": summary.execution_id,
        "status": summary.status,
        "mode": summary.mode,
        "started_at": summary.started_at,
        "stopped_at": summary.stopped_at,
        "workflow_version_id": summary.workflow_version_id,
        "endpoint": summary.endpoint,
        "publish_id": summary.publish_id,
        "delivery_status": summary.delivery_status,
        "send_result": summary.send_result,
        "adapter_response_type": summary.adapter_response_type,
        "adapter_status": summary.adapter_status,
        "product_name": summary.product_name,
        "target": summary.target,
        "image_url": summary.image_url,
        "copy_template": summary.copy_template,
        "copy_excerpt": summary.copy_excerpt,
    }
    for key, value in lines.items():
        if value not in (None, ""):
            print(f"INFO | {key}={value}")


def run(config: CheckConfig) -> int:
    payload = fetch_execution(config)
    summary = build_summary(payload, config.copy_chars)
    validate_summary(summary, config.expect_real_image)
    print_summary(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(config_from_args(parse_args(argv)))
    except (LastExecutionError, N8nOpsError, json.JSONDecodeError) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

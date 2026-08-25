from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ops_common import (
    REAL_GROUP_PINDATA,
    SAFE_PINDATA,
    TEST_PHONE_PINDATA,
    ComposeConfig,
    N8nOpsError,
    compact_json,
    compose_psql_command,
    dollar_quote,
    resolve_mode,
    sql_literal,
)

DEFAULT_WORKFLOW_JSON = Path("n8n/workflows/ofertas-mvp-supabase.json")
DEFAULT_COMPOSE_ENV = Path("/opt/automacao_grupo_compras/n8n/.env")
DEFAULT_COMPOSE_FILE = Path("/opt/automacao_grupo_compras/n8n/docker-compose.yml")
DEFAULT_WORKFLOW_ID = "OfertasMvpSupab1"
EXPECTED_TEMPLATE_TEXT = "Resgate o cupom desta"
EXPECTED_TEMPLATE_CODE_TEXT = r"Resgate o cupom desta p\u{00E1}gina"
EXPECTED_TEMPLATE_EMOJI_ESCAPES = (
    r"\u{1F525}",
    r"\u{1F3EA}",
    r"\u{1F4B5}",
    r"\u{1F3F7}",
    r"\u{2B50}",
    r"\u{1F39F}",
    r"\u{2705}",
)
EXPECTED_MESSAGE_LAYOUT = (
    r"\u{1F525} ${offer.product_name}"
    "\n\n"
    r"\u{1F4B5} ${formatMoney(offer.price)}"
    "\n"
    r"\u{1F3F7}\u{FE0F} ${discount}% OFF"
    "\n"
    r"\u{2B50} Avalia\u{00E7}\u{00E3}o: ${formatRating(offer.rating)}/5"
    "\n"
    r"\u{2705} Link do produto:"
    "\n"
    "${offer.offer_link}"
    "\n\n"
    r"\u{1F3EA} Loja: ${formatMarketplace(offer.marketplace)}"
    "\n"
    rf"\u{{1F39F}}\u{{FE0F}} {EXPECTED_TEMPLATE_CODE_TEXT}:"
    "\n"
    "${context.coupon_url}"
    "\n"
    r"(an\u{00FA}ncio)"
)
EXPECTED_SEND_IMAGE_PATH = "/api/sendImage"
FORBIDDEN_SEND_TEXT_PATH = "/api/sendText"
EXPECTED_SCHEDULE_CRON = "0 8-21 * * *"
EXPECTED_WORKFLOW_TIMEZONE = "America/Sao_Paulo"
EXPECTED_SCHEDULE_NODE = "Schedule Grupo Real"
EXPECTED_SCHEDULE_CONTEXT_NODE = "Set Contexto Schedule Grupo"
EXPECTED_SCHEDULE_LIMIT = 8
EXPECTED_SEND_DELAY_MIN = 45
EXPECTED_SEND_DELAY_MAX = 90
EXPECTED_LOOP_NODE = "Loop Ofertas"
EXPECTED_LOOP_RETURN_NODE = "Registrar Resultado Supabase"
EXPECTED_STATIC_SCHEDULE_NODE = "Schedule Mensagens Estaticas"
EXPECTED_STATIC_SCHEDULE_CRONS = (
    "30 9 * * *",
    "30 17 * * *",
)
EXPECTED_STATIC_ROOT_FOLDER = "ofertas-femininas"
EXPECTED_ONE_SHOT_SCHEDULE_NODE = "Schedule Mensagens Pontuais"
EXPECTED_ONE_SHOT_SCHEDULE_CRONS = (
    "45 17 * * *",
    "46 17 * * *",
    "47 17 * * *",
    "48 17 * * *",
)
EXPECTED_ONE_SHOT_ROOT_FOLDER = "ofertas-femininas-pendentes"
EXPECTED_ONE_SHOT_ARCHIVE_ROOT_FOLDER = "ofertas-femininas-enviados"
EXPECTED_STATIC_TARGET = "grupo-ofertas-feminino"
EXPECTED_STATIC_CHAT_ID = "120363412864266334@g.us"
EXPECTED_WAHA_CREDENTIAL = {"id": "wahad508ad814402", "name": "WAHA Header Auth"}
EXPECTED_POSTGRES_CREDENTIAL = {"id": "enHQciqlEESYRjQl", "name": "Postgres account"}

LEGACY_NODE_HASHES = {
    "1": "15d198952fd47d2837db4c8cd62b6829a62cb5d43fa0eb90dee1ac97c78e2500",
    "schedule-grupo-real": "586e739d19c4df6a21a2212f8bb3449e807b28cc34a5df9fcaf1ca4c1b2c4432",
    "schedule-context-grupo-real": (
        "9eaefb48ea187c08433b4780650689df65bcc38f53ac623fddf2b46c6389d035"
    ),
    "4": "b6a3df6df14099beb4467f60ccfaff9837a1173f11093a4b618489fea475507f",
    "prepare-batch-send": "b1f0ae87bec6f3b9cb50caa79b20fed928ce346ea53e951cef8a67176df4f795",
    "loop-send-offers": "e3dcdc1635ea655de6971288ffacfbcd866b30f847442b5fa8ee5c95b6022018",
    "5": "30f3570f5cac4bc7397dc1c1b6c68aa4b6ba41d59e910bb5afd73119d95747e7",
    "6": "2bdcc37a06cd7a87359619f9e21ea90ec35b50d2863defe2337aa29bdfa873c6",
    "8": "0dc88cebbdfd3f047769145301f9cc48e38eb802c0e32622f10794433ffd1bb7",
    "9": "84c95218ef2b80c7d0ce02ded369beb6e7ae40adfc4f1e5d3ffcfe6415626202",
    "3": "c1b49ff990d8e8c47f5c5787e3c89991c985c242076d432b1d33188f3346a80e",
    "962ad612-c9bc-46f1-a15a-0e24e25600ac": (
        "cbb267607daad2a25fcf9bd28b60926b2d99400c8a21e76bde89f5737e27ed38"
    ),
    "4dd3e336-768c-47b1-a62e-f2630dcbe663": (
        "6ddb0f866557d938100cee3b4d8242ff1e812b836a55ca1d725130b3746f258d"
    ),
    "waha-prepare-send": "7700145f8ed297db0d96ebad01bfd7ce848c792b6980631f1ad473d3a9367ffd",
    "waha-if-can-send": "85bbbfc64764f3f951f117c6ecc73ac438033ba8f38304fdf7af130a9c9e8210",
    "waha-wait-between-sends": "4a4fb26dd38c5a2eba74858e9d9e561dd116d90e30f9f9bdaaa3058d8105b2bf",
    "waha-send-text": "802adc36bc508061a1093509a6437db43a887fdb52a61a15a3e16a558277dcfe",
    "waha-normalize-result": "f9e1cbd91ff55520cd7f70096b95be52960ffcbecf258765749ea18384b68c57",
}

LEGACY_CONNECTION_HASHES = {
    "Trigger Manual": "03d22e8be82297f2af74c18a0c8fff16bb91e9960042f7488b410e19a18edd59",
    "Schedule Grupo Real": "8d3bee7eb369619a14b7bbbb18f03ae2f6f268c5af704b1a745de56aead13d86",
    "Set Contexto Schedule Grupo": (
        "e76542f6e649ee47dc5b100d37fef928d24ebff7646234d6119a7ee8fb84e399"
    ),
    "Consultar Fila Planejada Supabase": (
        "61a47e706804871a41f4631b08e403d753d2e0a3b1cdb6cdfb7e0b7e135e83a0"
    ),
    "Montar Mensagens": "151ad0f6113c9b1713ca00e2cb3fba874172e13cd29f15874121616ac0fa58a7",
    "Validar Allowlist": "b98f4ad3557219518791cac3aa360058733c58fea10c392cfa5e8279cf025b7b",
    "Montar Upsert Publication Event": (
        "507875c1067c38eff767af1545ff60bc8d50393f036f345d07cd82b60153a25f"
    ),
    "Validar Contexto": "9fbb8bcb4406e357b779c20ae396065855832ab9eb1b8f467e9bc14eb6b4a3aa",
    "Simular Envio MVP": "72e4ac3f0119f22dda4ad9b47ff7b1752ecface0ee748f03453c037edf563d0a",
    "Set Contexto MVP": "e76542f6e649ee47dc5b100d37fef928d24ebff7646234d6119a7ee8fb84e399",
    "Preparar Envio WAHA": "f225a37c9c8a0306a50ad650dadec494ede2e34fcc6a8b0d26bf1b6f04a4234e",
    "IF Pode Enviar WAHA": "3d5dbd935337ee2d53be66cb731b88b8fe2f3d8198637d6fd702aa3602410a31",
    "Enviar WhatsApp WAHA": "1bf60cfdb1428f70b96ab5c78f6a9dc919833e33a5d52b55220b3d01520bbec2",
    "Normalizar Resultado WAHA": "38bee10ff3a5d9df6033240107fbeb3260a07c151b0630cc5c43b90755c1f8c6",
    "Preparar Lote de Envio": "4cd132c8bf533b98dcfbbfcfa56febf281696c6184c39822979e8815043646b0",
    "Loop Ofertas": "c2c1b9edf42c9274aa8d972913890f43bf549ccfdd5d4a471cb57e3db6acb679",
    "Aguardar Intervalo WAHA": "c2a5325b26f866c19c94b88d18601d19f9c04a4f4eb68bdfbe927a4034dd237d",
    "Registrar Resultado Supabase": (
        "4cd132c8bf533b98dcfbbfcfa56febf281696c6184c39822979e8815043646b0"
    ),
}

STATIC_NODE_NAMES = {
    "Schedule Mensagens Estaticas",
    "Resolver Sequencia Estatica",
    "Buscar Pasta Raiz Drive",
    "Validar Pasta Raiz Drive",
    "IF Pasta Raiz Disponivel",
    "Buscar Pasta msg_XXX",
    "Validar Pasta msg_XXX",
    "IF Pasta msg_XXX Disponivel",
    "Buscar Arquivos msg_XXX",
    "Validar Arquivos msg_XXX",
    "IF Arquivos Completos",
    "Baixar copy.txt",
    "Baixar image.jpg",
    "Preparar Conteudo Estatico",
    "IF Conteudo Estatico Valido",
    "Preparar Envio WAHA Estatico",
    "IF Pode Enviar WAHA Estatico",
    "Enviar WhatsApp WAHA Estatico",
    "Normalizar Resultado WAHA Estatico",
    "Montar Upsert Publication Event Estatico",
    "Registrar Resultado Supabase Estatico",
}

STATIC_CONNECTION_TARGETS = {
    "Schedule Mensagens Estaticas": (("Resolver Sequencia Estatica",),),
    "Resolver Sequencia Estatica": (("Buscar Pasta Raiz Drive",),),
    "Buscar Pasta Raiz Drive": (("Validar Pasta Raiz Drive",),),
    "Validar Pasta Raiz Drive": (("IF Pasta Raiz Disponivel",),),
    "IF Pasta Raiz Disponivel": (
        ("Buscar Pasta msg_XXX",),
        ("Montar Upsert Publication Event Estatico",),
    ),
    "Buscar Pasta msg_XXX": (("Validar Pasta msg_XXX",),),
    "Validar Pasta msg_XXX": (("IF Pasta msg_XXX Disponivel",),),
    "IF Pasta msg_XXX Disponivel": (
        ("Buscar Arquivos msg_XXX",),
        ("Montar Upsert Publication Event Estatico",),
    ),
    "Buscar Arquivos msg_XXX": (("Validar Arquivos msg_XXX",),),
    "Validar Arquivos msg_XXX": (("IF Arquivos Completos",),),
    "IF Arquivos Completos": (
        ("Baixar copy.txt",),
        ("Montar Upsert Publication Event Estatico",),
    ),
    "Baixar copy.txt": (("Baixar image.jpg",),),
    "Baixar image.jpg": (("Preparar Conteudo Estatico",),),
    "Preparar Conteudo Estatico": (("IF Conteudo Estatico Valido",),),
    "IF Conteudo Estatico Valido": (
        ("Preparar Envio WAHA Estatico",),
        ("Montar Upsert Publication Event Estatico",),
    ),
    "Preparar Envio WAHA Estatico": (("IF Pode Enviar WAHA Estatico",),),
    "IF Pode Enviar WAHA Estatico": (
        ("Enviar WhatsApp WAHA Estatico",),
        ("Montar Upsert Publication Event Estatico",),
    ),
    "Enviar WhatsApp WAHA Estatico": (("Normalizar Resultado WAHA Estatico",),),
    "Normalizar Resultado WAHA Estatico": (("Montar Upsert Publication Event Estatico",),),
    "Montar Upsert Publication Event Estatico": (("Registrar Resultado Supabase Estatico",),),
}

ONE_SHOT_NODE_NAMES = {
    "Schedule Mensagens Pontuais",
    "Resolver Sequencia Pontual",
    "Buscar Pasta Pendentes Drive Pontual",
    "Validar Pasta Pendentes Drive Pontual",
    "IF Pasta Pendentes Disponivel Pontual",
    "Buscar Pasta msg_XXX Pontual",
    "Validar Pasta msg_XXX Pontual",
    "IF Pasta msg_XXX Disponivel Pontual",
    "Buscar Arquivos msg_XXX Pontual",
    "Validar Arquivos msg_XXX Pontual",
    "IF Arquivos Completos Pontual",
    "Baixar copy.txt Pontual",
    "Baixar image.jpg Pontual",
    "Preparar Conteudo Pontual",
    "IF Conteudo Pontual Valido",
    "Preparar Envio WAHA Pontual",
    "IF Pode Enviar WAHA Pontual",
    "Enviar WhatsApp WAHA Pontual",
    "Normalizar Resultado WAHA Pontual",
    "Montar Upsert Publication Event Pontual",
    "Registrar Resultado Supabase Pontual",
    "Preparar Arquivamento Pontual",
    "IF Deve Arquivar Pontual",
    "Buscar Pasta Enviados Drive Pontual",
    "Validar Pasta Enviados Drive Pontual",
    "IF Pasta Enviados Disponivel Pontual",
    "Buscar Pasta Dia Enviados Pontual",
    "Validar Pasta Dia Enviados Pontual",
    "IF Pasta Dia Enviados Pronta Pontual",
    "IF Criar Pasta Dia Enviados Pontual",
    "Criar Pasta Dia Enviados Pontual",
    "Normalizar Pasta Dia Criada Pontual",
    "Mover Pasta msg_XXX Pontual",
    "Normalizar Arquivamento Pontual",
    "Montar Update Arquivamento Pontual",
    "Atualizar Payload Arquivamento Pontual",
}

ONE_SHOT_CONNECTION_TARGETS = {
    "Schedule Mensagens Pontuais": (("Resolver Sequencia Pontual",),),
    "Resolver Sequencia Pontual": (("Buscar Pasta Pendentes Drive Pontual",),),
    "Buscar Pasta Pendentes Drive Pontual": (("Validar Pasta Pendentes Drive Pontual",),),
    "Validar Pasta Pendentes Drive Pontual": (("IF Pasta Pendentes Disponivel Pontual",),),
    "IF Pasta Pendentes Disponivel Pontual": (
        ("Buscar Pasta msg_XXX Pontual",),
        ("Montar Upsert Publication Event Pontual",),
    ),
    "Buscar Pasta msg_XXX Pontual": (("Validar Pasta msg_XXX Pontual",),),
    "Validar Pasta msg_XXX Pontual": (("IF Pasta msg_XXX Disponivel Pontual",),),
    "IF Pasta msg_XXX Disponivel Pontual": (
        ("Buscar Arquivos msg_XXX Pontual",),
        ("Montar Upsert Publication Event Pontual",),
    ),
    "Buscar Arquivos msg_XXX Pontual": (("Validar Arquivos msg_XXX Pontual",),),
    "Validar Arquivos msg_XXX Pontual": (("IF Arquivos Completos Pontual",),),
    "IF Arquivos Completos Pontual": (
        ("Baixar copy.txt Pontual",),
        ("Montar Upsert Publication Event Pontual",),
    ),
    "Baixar copy.txt Pontual": (("Baixar image.jpg Pontual",),),
    "Baixar image.jpg Pontual": (("Preparar Conteudo Pontual",),),
    "Preparar Conteudo Pontual": (("IF Conteudo Pontual Valido",),),
    "IF Conteudo Pontual Valido": (
        ("Preparar Envio WAHA Pontual",),
        ("Montar Upsert Publication Event Pontual",),
    ),
    "Preparar Envio WAHA Pontual": (("IF Pode Enviar WAHA Pontual",),),
    "IF Pode Enviar WAHA Pontual": (
        ("Enviar WhatsApp WAHA Pontual",),
        ("Montar Upsert Publication Event Pontual",),
    ),
    "Enviar WhatsApp WAHA Pontual": (("Normalizar Resultado WAHA Pontual",),),
    "Normalizar Resultado WAHA Pontual": (("Montar Upsert Publication Event Pontual",),),
    "Montar Upsert Publication Event Pontual": (("Registrar Resultado Supabase Pontual",),),
    "Registrar Resultado Supabase Pontual": (("Preparar Arquivamento Pontual",),),
    "Preparar Arquivamento Pontual": (("IF Deve Arquivar Pontual",),),
    "IF Deve Arquivar Pontual": (
        ("Buscar Pasta Enviados Drive Pontual",),
        ("Montar Update Arquivamento Pontual",),
    ),
    "Buscar Pasta Enviados Drive Pontual": (("Validar Pasta Enviados Drive Pontual",),),
    "Validar Pasta Enviados Drive Pontual": (("IF Pasta Enviados Disponivel Pontual",),),
    "IF Pasta Enviados Disponivel Pontual": (
        ("Buscar Pasta Dia Enviados Pontual",),
        ("Montar Update Arquivamento Pontual",),
    ),
    "Buscar Pasta Dia Enviados Pontual": (("Validar Pasta Dia Enviados Pontual",),),
    "Validar Pasta Dia Enviados Pontual": (("IF Pasta Dia Enviados Pronta Pontual",),),
    "IF Pasta Dia Enviados Pronta Pontual": (
        ("Mover Pasta msg_XXX Pontual",),
        ("IF Criar Pasta Dia Enviados Pontual",),
    ),
    "IF Criar Pasta Dia Enviados Pontual": (
        ("Criar Pasta Dia Enviados Pontual",),
        ("Montar Update Arquivamento Pontual",),
    ),
    "Criar Pasta Dia Enviados Pontual": (("Normalizar Pasta Dia Criada Pontual",),),
    "Normalizar Pasta Dia Criada Pontual": (("Mover Pasta msg_XXX Pontual",),),
    "Mover Pasta msg_XXX Pontual": (("Normalizar Arquivamento Pontual",),),
    "Normalizar Arquivamento Pontual": (("Montar Update Arquivamento Pontual",),),
    "Montar Update Arquivamento Pontual": (("Atualizar Payload Arquivamento Pontual",),),
}


class WorkflowGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeployConfig:
    workflow_json: Path
    workflow_id: str
    compose_env: Path
    compose_file: Path
    pin_data: dict[str, Any] | None
    dry_run: bool


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy and validate the guarded n8n workflow from the versioned JSON."
    )
    parser.add_argument("--workflow-json", type=Path, default=DEFAULT_WORKFLOW_JSON)
    parser.add_argument("--workflow-id", default=DEFAULT_WORKFLOW_ID)
    parser.add_argument("--compose-env", type=Path, default=DEFAULT_COMPOSE_ENV)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print a summary without changing n8n.",
    )
    parser.add_argument(
        "--mode",
        choices=("grupo-real", "teste-telefone", "dry-run", "preserve-pindata"),
        default="grupo-real",
        help="Operational pinData mode. Defaults to grupo-real.",
    )
    pin_group = parser.add_mutually_exclusive_group()
    pin_group.add_argument(
        "--safe-pindata",
        action="store_true",
        help="Set pinData to dry_run=true/teste-whatsapp instead of the real group.",
    )
    pin_group.add_argument(
        "--preserve-pindata",
        action="store_true",
        help="Do not update the pinData stored in n8n.",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> DeployConfig:
    pin_data: dict[str, Any] | None
    if args.preserve_pindata:
        pin_data = None
    elif args.safe_pindata:
        pin_data = SAFE_PINDATA
    else:
        pin_data = resolve_mode(args.mode).pin_data
    return DeployConfig(
        workflow_json=args.workflow_json,
        workflow_id=args.workflow_id,
        compose_env=args.compose_env,
        compose_file=args.compose_file,
        pin_data=pin_data,
        dry_run=args.dry_run,
    )


def load_workflow(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise WorkflowGuardError(f"workflow JSON not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowGuardError(f"invalid workflow JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WorkflowGuardError("workflow JSON must be an object")
    return payload


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


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_legacy_immutable(workflow: dict[str, Any], errors: list[str]) -> None:
    nodes = workflow.get("nodes")
    connections = workflow.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, dict):
        return

    nodes_by_id = {
        node.get("id"): node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    for node_id, expected_hash in LEGACY_NODE_HASHES.items():
        node = nodes_by_id.get(node_id)
        if node is None:
            errors.append(f"legacy node missing: {node_id}")
        elif canonical_hash(node) != expected_hash:
            errors.append(f"legacy node modified: {node.get('name', node_id)}")

    for source, expected_hash in LEGACY_CONNECTION_HASHES.items():
        connection = connections.get(source)
        if connection is None:
            errors.append(f"legacy connection source missing: {source}")
        elif canonical_hash(connection) != expected_hash:
            errors.append(f"legacy connections modified: {source}")


def connection_targets(connection: Any) -> tuple[tuple[str, ...], ...]:
    if not isinstance(connection, dict):
        return ()
    outputs = connection.get("main")
    if not isinstance(outputs, list):
        return ()
    return tuple(
        tuple(edge.get("node", "") for edge in output if isinstance(edge, dict))
        for output in outputs
        if isinstance(output, list)
    )


def validate_static_messages(workflow: dict[str, Any], errors: list[str]) -> None:
    nodes = workflow.get("nodes")
    connections = workflow.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, dict):
        return

    if workflow.get("active") is not False:
        errors.append("versioned workflow active must be false")

    static_nodes = [
        node
        for node in nodes
        if isinstance(node, dict) and str(node.get("id", "")).startswith("static-")
    ]
    static_names = {str(node.get("name", "")) for node in static_nodes}
    if static_names != STATIC_NODE_NAMES:
        missing = sorted(STATIC_NODE_NAMES - static_names)
        unexpected = sorted(static_names - STATIC_NODE_NAMES)
        errors.append(f"static node set mismatch: missing={missing}, unexpected={unexpected}")
    if len(nodes) != len(LEGACY_NODE_HASHES) + len(STATIC_NODE_NAMES) + len(
        ONE_SHOT_NODE_NAMES
    ):
        errors.append("workflow must contain exactly 18 legacy, 21 static, and 36 one-shot nodes")

    schedule_nodes = [
        node
        for node in nodes
        if isinstance(node, dict) and node.get("type") == "n8n-nodes-base.scheduleTrigger"
    ]
    static_schedule_nodes = [
        node for node in schedule_nodes if str(node.get("id", "")).startswith("static-")
    ]
    static_schedule = node_by_name(workflow, EXPECTED_STATIC_SCHEDULE_NODE)
    if len(static_schedule_nodes) != 1 or static_schedule is None:
        errors.append("workflow must contain exactly one static Schedule Trigger")
    else:
        intervals = static_schedule.get("parameters", {}).get("rule", {}).get("interval", [])
        expressions = tuple(
            interval.get("expression")
            for interval in intervals
            if isinstance(interval, dict) and interval.get("field") == "cronExpression"
        )
        if expressions != EXPECTED_STATIC_SCHEDULE_CRONS:
            errors.append("static schedule must contain the approved cron rules")

    resolver = node_by_name(workflow, "Resolver Sequencia Estatica")
    resolver_code = str((resolver or {}).get("parameters", {}).get("jsCode", ""))
    for expected in (
        "$getWorkflowStaticData('node')",
        "static_message_day",
        "static_message_sequence",
        "padStart(3, '0')",
        f"root_folder_name: '{EXPECTED_STATIC_ROOT_FOLDER}'",
        "marketplace: 'google-drive'",
        f"target: '{EXPECTED_STATIC_TARGET}'",
        f"target_chat_id: '{EXPECTED_STATIC_CHAT_ID}'",
    ):
        if expected not in resolver_code:
            errors.append(f"static sequence resolver missing {expected}")

    google_node_names = (
        "Buscar Pasta Raiz Drive",
        "Buscar Pasta msg_XXX",
        "Buscar Arquivos msg_XXX",
        "Baixar copy.txt",
        "Baixar image.jpg",
    )
    google_nodes = [node_by_name(workflow, name) for name in google_node_names]
    for name, node in zip(google_node_names, google_nodes, strict=True):
        if node is None or node.get("type") != "n8n-nodes-base.googleDrive":
            errors.append(f"missing Google Drive node: {name}")
            continue
        if node.get("typeVersion") != 3:
            errors.append(f"Google Drive node must use typeVersion 3: {name}")
        if node.get("credentials"):
            errors.append(f"Google Drive credential must not be versioned: {name}")
        if node.get("parameters", {}).get("authentication") != "oAuth2":
            errors.append(f"Google Drive node must use OAuth2: {name}")

    file_validator = node_by_name(workflow, "Validar Arquivos msg_XXX")
    file_validator_code = str((file_validator or {}).get("parameters", {}).get("jsCode", ""))
    for expected in ("copy.txt", "image.jpg", "text/plain", "image/jpeg"):
        if expected not in file_validator_code:
            errors.append(f"static file validation missing {expected}")

    content_node = node_by_name(workflow, "Preparar Conteudo Estatico")
    content_code = str((content_node or {}).get("parameters", {}).get("jsCode", ""))
    for expected in ("getBinaryDataBuffer", "copy_file", "image_file", "toString('base64')"):
        if expected not in content_code:
            errors.append(f"static content preparation missing {expected}")

    waha_node = node_by_name(workflow, "Enviar WhatsApp WAHA Estatico")
    waha_parameters = (waha_node or {}).get("parameters", {})
    if waha_parameters.get("url") != "http://waha:3000/api/sendImage":
        errors.append("static WAHA node must reuse /api/sendImage")
    waha_body = str(waha_parameters.get("jsonBody", ""))
    for expected in ("session: 'default'", "data: $json.waha_image_base64"):
        if expected not in waha_body:
            errors.append(f"static WAHA payload missing {expected}")
    if (waha_node or {}).get("credentials", {}).get("httpHeaderAuth") != EXPECTED_WAHA_CREDENTIAL:
        errors.append("static WAHA node must reuse WAHA Header Auth")

    register_node = node_by_name(workflow, "Registrar Resultado Supabase Estatico")
    if (register_node or {}).get("credentials", {}).get("postgres") != EXPECTED_POSTGRES_CREDENTIAL:
        errors.append("static register node must reuse Postgres account")

    upsert_node = node_by_name(workflow, "Montar Upsert Publication Event Estatico")
    upsert_code = str((upsert_node or {}).get("parameters", {}).get("jsCode", ""))
    for expected in (
        "offers.publication_events",
        "delivery_status || 'cancelled'",
        "on conflict (profile, target, manifest_item_number, artifact_generated_at)",
        "source: 'google_drive_static_message'",
    ):
        if expected not in upsert_code:
            errors.append(f"static publication upsert missing {expected}")

    for source, expected_targets in STATIC_CONNECTION_TARGETS.items():
        actual_targets = connection_targets(connections.get(source))
        if actual_targets != expected_targets:
            errors.append(f"static connections modified: {source}")

    unexpected_static_sources = {
        source
        for source in connections
        if source in STATIC_NODE_NAMES and source not in STATIC_CONNECTION_TARGETS
    }
    if unexpected_static_sources:
        errors.append(f"unexpected static connection sources: {sorted(unexpected_static_sources)}")


def validate_one_shot_messages(workflow: dict[str, Any], errors: list[str]) -> None:
    nodes = workflow.get("nodes")
    connections = workflow.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, dict):
        return

    one_shot_nodes = [
        node
        for node in nodes
        if isinstance(node, dict) and str(node.get("id", "")).startswith("one-shot-")
    ]
    one_shot_names = {str(node.get("name", "")) for node in one_shot_nodes}
    if one_shot_names != ONE_SHOT_NODE_NAMES:
        missing = sorted(ONE_SHOT_NODE_NAMES - one_shot_names)
        unexpected = sorted(one_shot_names - ONE_SHOT_NODE_NAMES)
        errors.append(f"one-shot node set mismatch: missing={missing}, unexpected={unexpected}")

    schedule_nodes = [
        node
        for node in nodes
        if isinstance(node, dict) and node.get("type") == "n8n-nodes-base.scheduleTrigger"
    ]
    one_shot_schedule = node_by_name(workflow, EXPECTED_ONE_SHOT_SCHEDULE_NODE)
    if len(schedule_nodes) != 3 or one_shot_schedule is None:
        errors.append("workflow must contain exactly one one-shot Schedule Trigger")
    else:
        intervals = one_shot_schedule.get("parameters", {}).get("rule", {}).get("interval", [])
        expressions = tuple(
            interval.get("expression")
            for interval in intervals
            if isinstance(interval, dict) and interval.get("field") == "cronExpression"
        )
        if expressions != EXPECTED_ONE_SHOT_SCHEDULE_CRONS:
            errors.append("one-shot schedule must contain the approved cron rules")

    resolver = node_by_name(workflow, "Resolver Sequencia Pontual")
    resolver_code = str((resolver or {}).get("parameters", {}).get("jsCode", ""))
    for expected in (
        "$getWorkflowStaticData('node')",
        "one_shot_message_day",
        "one_shot_message_sequence",
        "padStart(3, '0')",
        f"root_folder_name: '{EXPECTED_ONE_SHOT_ROOT_FOLDER}'",
        f"archive_root_folder_name: '{EXPECTED_ONE_SHOT_ARCHIVE_ROOT_FOLDER}'",
        "message_flow_type: 'static_one_shot'",
        "marketplace: 'google-drive'",
        f"target: '{EXPECTED_STATIC_TARGET}'",
        f"target_chat_id: '{EXPECTED_STATIC_CHAT_ID}'",
    ):
        if expected not in resolver_code:
            errors.append(f"one-shot sequence resolver missing {expected}")

    google_node_names = (
        "Buscar Pasta Pendentes Drive Pontual",
        "Buscar Pasta msg_XXX Pontual",
        "Buscar Arquivos msg_XXX Pontual",
        "Baixar copy.txt Pontual",
        "Baixar image.jpg Pontual",
        "Buscar Pasta Enviados Drive Pontual",
        "Buscar Pasta Dia Enviados Pontual",
        "Criar Pasta Dia Enviados Pontual",
        "Mover Pasta msg_XXX Pontual",
    )
    for name in google_node_names:
        node = node_by_name(workflow, name)
        if node is None or node.get("type") != "n8n-nodes-base.googleDrive":
            errors.append(f"missing one-shot Google Drive node: {name}")
            continue
        if node.get("typeVersion") != 3:
            errors.append(f"one-shot Google Drive node must use typeVersion 3: {name}")
        if node.get("credentials"):
            errors.append(f"one-shot Google Drive credential must not be versioned: {name}")
        if node.get("parameters", {}).get("authentication") != "oAuth2":
            errors.append(f"one-shot Google Drive node must use OAuth2: {name}")

    pending_root = node_by_name(workflow, "Buscar Pasta Pendentes Drive Pontual")
    if EXPECTED_ONE_SHOT_ROOT_FOLDER not in str(
        (pending_root or {}).get("parameters", {}).get("queryString", "")
    ):
        errors.append("one-shot pending root search must use ofertas-femininas-pendentes")

    archive_root = node_by_name(workflow, "Buscar Pasta Enviados Drive Pontual")
    if EXPECTED_ONE_SHOT_ARCHIVE_ROOT_FOLDER not in str(
        (archive_root or {}).get("parameters", {}).get("queryString", "")
    ):
        errors.append("one-shot archive root search must use ofertas-femininas-enviados")

    create_day = node_by_name(workflow, "Criar Pasta Dia Enviados Pontual")
    create_params = (create_day or {}).get("parameters", {})
    if (
        create_params.get("resource") != "folder"
        or create_params.get("operation") != "create"
        or str(create_params.get("name")) != "={{ $json.execution_day }}"
        or str(create_params.get("folderId", {}).get("value"))
        != "={{ $json.archive_root_folder_id }}"
    ):
        errors.append("one-shot archive day folder must be created under archive root")

    move_node = node_by_name(workflow, "Mover Pasta msg_XXX Pontual")
    move_params = (move_node or {}).get("parameters", {})
    if (
        move_params.get("resource") != "file"
        or move_params.get("operation") != "move"
        or str(move_params.get("fileId", {}).get("value")) != "={{ $json.message_folder_id }}"
        or str(move_params.get("folderId", {}).get("value")) != "={{ $json.archive_parent_id }}"
    ):
        errors.append("one-shot move node must move msg_XXX folder to archive day folder")

    file_validator = node_by_name(workflow, "Validar Arquivos msg_XXX Pontual")
    file_validator_code = str((file_validator or {}).get("parameters", {}).get("jsCode", ""))
    for expected in ("copy.txt", "image.jpg", "text/plain", "image/jpeg"):
        if expected not in file_validator_code:
            errors.append(f"one-shot file validation missing {expected}")

    content_node = node_by_name(workflow, "Preparar Conteudo Pontual")
    content_code = str((content_node or {}).get("parameters", {}).get("jsCode", ""))
    for expected in ("getBinaryDataBuffer", "copy_file", "image_file", "toString('base64')"):
        if expected not in content_code:
            errors.append(f"one-shot content preparation missing {expected}")

    prepare_archive = node_by_name(workflow, "Preparar Arquivamento Pontual")
    prepare_archive_code = str((prepare_archive or {}).get("parameters", {}).get("jsCode", ""))
    for expected in (
        "$('Montar Upsert Publication Event Pontual').first().json",
        "source.delivery_status === 'confirmed'",
        "archive_should_move",
    ):
        if expected not in prepare_archive_code:
            errors.append(f"one-shot archive preparation missing {expected}")

    waha_node = node_by_name(workflow, "Enviar WhatsApp WAHA Pontual")
    waha_parameters = (waha_node or {}).get("parameters", {})
    if waha_parameters.get("url") != "http://waha:3000/api/sendImage":
        errors.append("one-shot WAHA node must reuse /api/sendImage")
    waha_body = str(waha_parameters.get("jsonBody", ""))
    for expected in ("session: 'default'", "data: $json.waha_image_base64"):
        if expected not in waha_body:
            errors.append(f"one-shot WAHA payload missing {expected}")
    if (waha_node or {}).get("credentials", {}).get("httpHeaderAuth") != EXPECTED_WAHA_CREDENTIAL:
        errors.append("one-shot WAHA node must reuse WAHA Header Auth")

    for name in (
        "Registrar Resultado Supabase Pontual",
        "Atualizar Payload Arquivamento Pontual",
    ):
        node = node_by_name(workflow, name)
        if (node or {}).get("credentials", {}).get("postgres") != EXPECTED_POSTGRES_CREDENTIAL:
            errors.append(f"one-shot Postgres node must reuse Postgres account: {name}")

    upsert_node = node_by_name(workflow, "Montar Upsert Publication Event Pontual")
    upsert_code = str((upsert_node or {}).get("parameters", {}).get("jsCode", ""))
    for expected in (
        "offers.publication_events",
        "delivery_status || 'cancelled'",
        "on conflict (profile, target, manifest_item_number, artifact_generated_at)",
        "source: 'google_drive_static_one_shot'",
        "message_flow_type",
        "archive_status",
    ):
        if expected not in upsert_code:
            errors.append(f"one-shot publication upsert missing {expected}")

    archive_update = node_by_name(workflow, "Montar Update Arquivamento Pontual")
    archive_update_code = str((archive_update or {}).get("parameters", {}).get("jsCode", ""))
    for expected in (
        "update offers.publication_events",
        "coalesce(payload, '{}'::jsonb)",
        "archive_status",
        "archive_folder_id",
        "archive_parent_id",
        "archive_error",
        "where publish_id",
    ):
        if expected not in archive_update_code:
            errors.append(f"one-shot archive update missing {expected}")

    for source, expected_targets in ONE_SHOT_CONNECTION_TARGETS.items():
        actual_targets = connection_targets(connections.get(source))
        if actual_targets != expected_targets:
            errors.append(f"one-shot connections modified: {source}")

    unexpected_one_shot_sources = {
        source
        for source in connections
        if source in ONE_SHOT_NODE_NAMES and source not in ONE_SHOT_CONNECTION_TARGETS
    }
    if unexpected_one_shot_sources:
        errors.append(
            f"unexpected one-shot connection sources: {sorted(unexpected_one_shot_sources)}"
        )


def validate_schedule(workflow: dict[str, Any], errors: list[str]) -> None:
    schedule_node = node_by_name(workflow, EXPECTED_SCHEDULE_NODE)
    if schedule_node is None:
        errors.append(f"missing schedule node: {EXPECTED_SCHEDULE_NODE}")
        return
    if schedule_node.get("type") != "n8n-nodes-base.scheduleTrigger":
        errors.append(f"{EXPECTED_SCHEDULE_NODE} must be scheduleTrigger")
    intervals = schedule_node.get("parameters", {}).get("rule", {}).get("interval", [])
    cron_expressions = [
        item.get("expression")
        for item in intervals
        if isinstance(item, dict) and item.get("field") == "cronExpression"
    ]
    if EXPECTED_SCHEDULE_CRON not in cron_expressions:
        errors.append(f"{EXPECTED_SCHEDULE_NODE} cron must include {EXPECTED_SCHEDULE_CRON}")

    schedule_context = node_by_name(workflow, EXPECTED_SCHEDULE_CONTEXT_NODE)
    if schedule_context is None:
        errors.append(f"missing schedule context node: {EXPECTED_SCHEDULE_CONTEXT_NODE}")
    else:
        context_code = str(schedule_context.get("parameters", {}).get("jsCode", ""))
        for expected_text in (
            "dry_run: false",
            f"limit: {EXPECTED_SCHEDULE_LIMIT}",
            "target: 'grupo-ofertas-feminino'",
            "target_chat_id: '120363412864266334@g.us'",
            "allowed_targets_csv: 'grupo-ofertas-feminino'",
            f"send_delay_seconds_min: {EXPECTED_SEND_DELAY_MIN}",
            f"send_delay_seconds_max: {EXPECTED_SEND_DELAY_MAX}",
            "schedule-grupo-real",
        ):
            if expected_text not in context_code:
                errors.append(f"{EXPECTED_SCHEDULE_CONTEXT_NODE} missing {expected_text}")

    connections = workflow.get("connections")
    if isinstance(connections, dict):
        schedule_connections = json.dumps(
            connections.get(EXPECTED_SCHEDULE_NODE, {}),
            ensure_ascii=False,
        )
        context_connections = json.dumps(
            connections.get(EXPECTED_SCHEDULE_CONTEXT_NODE, {}),
            ensure_ascii=False,
        )
        if EXPECTED_SCHEDULE_CONTEXT_NODE not in schedule_connections:
            errors.append(
                f"{EXPECTED_SCHEDULE_NODE} must connect to {EXPECTED_SCHEDULE_CONTEXT_NODE}"
            )
        if "Validar Contexto" not in context_connections:
            errors.append(f"{EXPECTED_SCHEDULE_CONTEXT_NODE} must connect to Validar Contexto")

    settings = workflow.get("settings")
    if not isinstance(settings, dict) or settings.get("timezone") != EXPECTED_WORKFLOW_TIMEZONE:
        errors.append(f"workflow timezone must be {EXPECTED_WORKFLOW_TIMEZONE}")


def validate_send_loop(workflow: dict[str, Any], errors: list[str]) -> None:
    connections = workflow.get("connections")
    if not isinstance(connections, dict):
        return

    loop_main = connections.get(EXPECTED_LOOP_NODE, {}).get("main", [])
    loop_output = loop_main[1] if len(loop_main) > 1 else []
    if not any(
        connection.get("node") == "Montar Mensagens"
        for connection in loop_output
        if isinstance(connection, dict)
    ):
        errors.append(f"{EXPECTED_LOOP_NODE} loop output must connect to Montar Mensagens")

    return_main = connections.get(EXPECTED_LOOP_RETURN_NODE, {}).get("main", [])
    return_output = return_main[0] if return_main else []
    if not any(
        connection.get("node") == EXPECTED_LOOP_NODE
        for connection in return_output
        if isinstance(connection, dict)
    ):
        errors.append(f"{EXPECTED_LOOP_RETURN_NODE} must connect back to {EXPECTED_LOOP_NODE}")


def validate_daily_plan_claim(workflow: dict[str, Any], errors: list[str]) -> None:
    context_node = node_by_name(workflow, "Validar Contexto")
    if context_node is None:
        errors.append("missing context node: Validar Contexto")
        return
    context_code = str(context_node.get("parameters", {}).get("jsCode", "")).lower()
    for expected_text in (
        "offers.daily_dispatch_plan",
        "offers.v_daily_dispatch_ready",
        "for update of plan skip locked",
        "ready.is_ready_for_dispatch",
        "dispatch_status = 'claimed'",
        "claim_token",
        "null::uuid as dispatch_plan_id",
        "dryrun ? previewquery : claimquery",
    ):
        if expected_text not in context_code:
            errors.append(f"Validar Contexto missing atomic claim: {expected_text}")


def validate_message_template(workflow: dict[str, Any], errors: list[str]) -> None:
    message_node = node_by_name(workflow, "Montar Mensagens")
    if message_node is None:
        errors.append("missing message node: Montar Mensagens")
        return

    message_code = str(message_node.get("parameters", {}).get("jsCode", ""))
    for emoji_escape in EXPECTED_TEMPLATE_EMOJI_ESCAPES:
        if emoji_escape not in message_code:
            errors.append(f"Montar Mensagens missing emoji escape {emoji_escape}")
    if EXPECTED_MESSAGE_LAYOUT not in message_code:
        errors.append("Montar Mensagens does not match the compact copy layout")


def validate_versioned_workflow(workflow: dict[str, Any], workflow_id: str) -> None:
    errors: list[str] = []
    if workflow.get("id") != workflow_id:
        errors.append(f"workflow id mismatch: expected {workflow_id}, got {workflow.get('id')}")
    if not isinstance(workflow.get("nodes"), list):
        errors.append("workflow nodes must be a list")
    if not isinstance(workflow.get("connections"), dict):
        errors.append("workflow connections must be an object")

    text = workflow_text(workflow)
    if EXPECTED_SEND_IMAGE_PATH not in text:
        errors.append(f"missing {EXPECTED_SEND_IMAGE_PATH}")
    if FORBIDDEN_SEND_TEXT_PATH in text:
        errors.append(f"forbidden {FORBIDDEN_SEND_TEXT_PATH} found")
    if EXPECTED_TEMPLATE_TEXT not in text:
        errors.append(f"missing template text: {EXPECTED_TEMPLATE_TEXT}")

    validate_legacy_immutable(workflow, errors)
    validate_static_messages(workflow, errors)
    validate_one_shot_messages(workflow, errors)
    validate_schedule(workflow, errors)
    validate_send_loop(workflow, errors)
    validate_daily_plan_claim(workflow, errors)
    validate_message_template(workflow, errors)

    if errors:
        raise WorkflowGuardError("; ".join(errors))


def validate_pin_data(pin_data: dict[str, Any] | None) -> None:
    if pin_data is None:
        return
    try:
        payload = pin_data["Trigger Manual"][0]["json"]
    except (KeyError, IndexError, TypeError) as exc:
        raise WorkflowGuardError("pinData must contain Trigger Manual[0].json") from exc

    if not isinstance(payload.get("dry_run"), bool):
        raise WorkflowGuardError("pinData dry_run must be boolean")

    chat_id = payload.get("target_chat_id")
    if payload.get("dry_run") is False and not str(chat_id).endswith(("@g.us", "@c.us")):
        raise WorkflowGuardError("real pinData target_chat_id must end with @g.us or @c.us")


def build_update_sql(
    workflow: dict[str, Any],
    workflow_id: str,
    pin_data: dict[str, Any] | None,
) -> str:
    required_fields = ("nodes", "connections")
    missing = [field for field in required_fields if field not in workflow]
    if missing:
        raise WorkflowGuardError(f"workflow missing required fields: {missing}")

    assignments = [
        f"nodes = {dollar_quote(compact_json(workflow['nodes']))}::json",
        f"connections = {dollar_quote(compact_json(workflow['connections']))}::json",
        f"settings = {dollar_quote(compact_json(workflow.get('settings', {})))}::json",
        "active = false",
        '"versionId" = gen_random_uuid()::text',
        '"versionCounter" = coalesce("versionCounter", 0) + 1',
        '"updatedAt" = now()',
    ]
    if pin_data is not None:
        assignments.insert(
            3,
            f'"pinData" = {dollar_quote(compact_json(pin_data))}::json',
        )

    return (
        "with updated_workflow as (\n"
        "  update workflow_entity\n"
        f"  set {', '.join(assignments)}\n"
        f"  where id = {sql_literal(workflow_id)}\n"
        '  returning id, "versionId", name, nodes, connections, "updatedAt"\n'
        ")\n"
        "insert into workflow_history (\n"
        '  "versionId", "workflowId", authors, "createdAt", "updatedAt",\n'
        '  nodes, connections, name, autosaved, description, "nodeGroups"\n'
        ")\n"
        "select\n"
        '  updated."versionId", updated.id,\n'
        "  coalesce((\n"
        "    select history.authors\n"
        "    from workflow_history history\n"
        '    where history."workflowId" = updated.id\n'
        '    order by history."createdAt" desc\n'
        "    limit 1\n"
        "  ), 'system'),\n"
        '  updated."updatedAt", updated."updatedAt", updated.nodes,\n'
        "  updated.connections, updated.name, false, null, '[]'::json\n"
        "from updated_workflow updated;"
    )


def build_status_query(workflow_id: str) -> str:
    return (
        "select json_build_object("
        "'id', id, "
        "'active', active, "
        "'versionId', \"versionId\", "
        "'versionCounter', \"versionCounter\", "
        "'updatedAt', \"updatedAt\", "
        "'has_new_copy', position('Resgate o cupom desta' in nodes::text) > 0, "
        "'has_send_image', position('/api/sendImage' in nodes::text) > 0, "
        "'has_send_text', position('/api/sendText' in nodes::text) > 0, "
        "'history_exists', exists ("
        "select 1 from workflow_history history "
        'where history."workflowId" = workflow_entity.id '
        'and history."versionId" = workflow_entity."versionId"'
        "), "
        "'pinData', \"pinData\""
        ")::text "
        "from workflow_entity "
        f"where id = {sql_literal(workflow_id)};"
    )


def run_update(sql: str, config: DeployConfig) -> None:
    completed = subprocess.run(
        compose_psql_command(ComposeConfig(config.compose_env, config.compose_file)),
        input=sql,
        text=True,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise WorkflowGuardError(
            f"failed to update n8n workflow:\nstdout={completed.stdout}\nstderr={completed.stderr}"
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
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise WorkflowGuardError(
            "failed to fetch n8n workflow status:\n"
            f"stdout={completed.stdout}\n"
            f"stderr={completed.stderr}"
        )
    output = completed.stdout.strip()
    if not output:
        raise WorkflowGuardError(f"workflow not found in n8n: {config.workflow_id}")
    try:
        status = json.loads(output)
    except json.JSONDecodeError as exc:
        raise WorkflowGuardError(f"invalid status JSON from psql: {output}") from exc
    if not isinstance(status, dict):
        raise WorkflowGuardError("status query did not return an object")
    return status


def validate_deployed_status(status: dict[str, Any], pin_data: dict[str, Any] | None) -> None:
    errors: list[str] = []
    if status.get("active") is not False:
        errors.append("active must be false")
    if status.get("has_send_image") is not True:
        errors.append("sendImage must be present")
    if status.get("has_send_text") is not False:
        errors.append("sendText must be absent")
    if status.get("has_new_copy") is not True:
        errors.append(f"template must contain {EXPECTED_TEMPLATE_TEXT}")
    if status.get("history_exists") is not True:
        errors.append("current version must exist in workflow_history")

    if pin_data is not None:
        deployed_pin_data = status.get("pinData")
        if deployed_pin_data != pin_data:
            errors.append("deployed pinData does not match requested pinData")
        else:
            try:
                payload = deployed_pin_data["Trigger Manual"][0]["json"]
            except (KeyError, IndexError, TypeError):
                errors.append("deployed pinData is malformed")
            else:
                if payload.get("dry_run") is not False and pin_data == REAL_GROUP_PINDATA:
                    errors.append("real group pinData must use dry_run=false")
                chat_id = payload.get("target_chat_id")
                if payload.get("dry_run") is False and not str(chat_id).endswith(
                    ("@g.us", "@c.us")
                ):
                    errors.append("real pinData target_chat_id must end with @g.us or @c.us")

    if errors:
        raise WorkflowGuardError("; ".join(errors))


def print_summary(status: dict[str, Any] | None, pin_data: dict[str, Any] | None) -> None:
    def pin_mode_name(value: dict[str, Any] | None) -> str:
        if value is None:
            return "preserve"
        if value == SAFE_PINDATA:
            return "safe"
        if value == TEST_PHONE_PINDATA:
            return "teste telefone"
        if value == REAL_GROUP_PINDATA:
            return "grupo real"
        return "custom"

    if status is None:
        mode = pin_mode_name(pin_data)
        print("INFO | dry_run=true; no changes applied")
        print(f"INFO | pinData mode={mode}")
        print("INFO | local workflow sendImage=ok")
        print("INFO | local workflow sendText=absent")
        print("INFO | local workflow template=ok")
        return

    pin_mode = pin_mode_name(status.get("pinData"))
    print(f"INFO | workflow_id={status.get('id')}")
    print(f"INFO | versionId={status.get('versionId')}")
    print(f"INFO | versionCounter={status.get('versionCounter')}")
    print(f"INFO | active={str(status.get('active')).lower()}")
    print(f"INFO | history_exists={str(status.get('history_exists')).lower()}")
    print("INFO | sendImage=ok")
    print("INFO | sendText=absent")
    print("INFO | template=ok")
    print(f"INFO | pinData={pin_mode}")


def run(config: DeployConfig) -> int:
    workflow = load_workflow(config.workflow_json)
    validate_versioned_workflow(workflow, config.workflow_id)
    validate_pin_data(config.pin_data)
    sql = build_update_sql(workflow, config.workflow_id, config.pin_data)

    if config.dry_run:
        print_summary(None, config.pin_data)
        print(f"INFO | sql_bytes={len(sql.encode('utf-8'))}")
        return 0

    run_update(sql, config)
    status = fetch_status(config)
    validate_deployed_status(status, config.pin_data)
    print_summary(status, config.pin_data)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(config_from_args(parse_args(argv)))
    except (WorkflowGuardError, N8nOpsError) as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

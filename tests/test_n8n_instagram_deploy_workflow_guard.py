from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/n8n/deploy_instagram_workflow_guard.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("deploy_instagram_workflow_guard", MODULE_PATH)
assert SPEC is not None
guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)


def load_instagram_workflow() -> dict[str, object]:
    return guard.load_workflow(Path("n8n/workflows/ofertas-instagram-supabase.json"))


def test_validate_instagram_workflow_accepts_versioned_json() -> None:
    guard.validate_versioned_workflow(load_instagram_workflow(), "OfertasInstagramSupab1")


def test_validate_instagram_workflow_rejects_missing_carousel_branch() -> None:
    workflow = load_instagram_workflow()
    workflow["nodes"] = [
        node for node in workflow["nodes"] if node["name"] != "Normalizar Container Criado"
    ]

    with pytest.raises(guard.InstagramWorkflowGuardError, match="Normalizar Container Criado"):
        guard.validate_versioned_workflow(workflow, "OfertasInstagramSupab1")


def test_validate_instagram_workflow_rejects_waha_endpoint() -> None:
    workflow = load_instagram_workflow()
    workflow["nodes"].append(
        {
            "name": "Enviar WhatsApp WAHA",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {"url": "http://waha:3000/api/sendImage"},
        }
    )

    with pytest.raises(guard.InstagramWorkflowGuardError, match="forbidden"):
        guard.validate_versioned_workflow(workflow, "OfertasInstagramSupab1")


def test_validate_instagram_workflow_rejects_missing_postgres_credentials() -> None:
    workflow = load_instagram_workflow()
    for node in workflow["nodes"]:
        if node["name"] == "Claim Item Instagram":
            node.pop("credentials", None)
            break

    with pytest.raises(guard.InstagramWorkflowGuardError, match="missing postgres"):
        guard.validate_versioned_workflow(workflow, "OfertasInstagramSupab1")


def test_validate_instagram_workflow_requires_dry_run_gate_before_http_nodes() -> None:
    workflow = load_instagram_workflow()
    workflow["connections"]["Revalidar Midia"]["main"] = [
        [
            {"node": "Roteador Formato", "type": "main", "index": 0},
            {"node": "Marcar Midia Expirada", "type": "main", "index": 0},
        ]
    ]

    with pytest.raises(guard.InstagramWorkflowGuardError, match="Dry Run Instagram"):
        guard.validate_versioned_workflow(workflow, "OfertasInstagramSupab1")


def test_instagram_claim_query_preserves_dry_run_context() -> None:
    workflow = load_instagram_workflow()
    claim_node = guard.node_by_name(workflow, "Claim Item Instagram")
    query = claim_node["parameters"]["query"]

    assert "nullif" in query
    assert "context.dry_run" in query
    assert "ctx.dry_run" in query
    assert "ctx.instagram_business_account_id" in query
    assert (
        "nullif('{{ $json.instagram_business_account_id || \"\" }}', '')::text as "
        "instagram_business_account_id" in query
    )
    assert "ctx.whatsapp_group_url" in query
    assert "nullif('{{ $json.whatsapp_group_url || \"\" }}', '')::text as whatsapp_group_url" in query
    assert "case when ctx.dry_run then 'cancelled'" in query
    assert "ready.planned_date <= (now() at time zone 'america/sao_paulo')::date" in query.lower()
    assert "order by ready.planned_date, ready.daily_sequence, ready.instagram_format desc" in query


def test_validate_instagram_workflow_requires_http_header_auth_credentials() -> None:
    workflow = load_instagram_workflow()
    reels_node = guard.node_by_name(workflow, "Criar Container Reels")
    reels_node.pop("credentials", None)

    with pytest.raises(guard.InstagramWorkflowGuardError, match="httpHeaderAuth"):
        guard.validate_versioned_workflow(workflow, "OfertasInstagramSupab1")


def test_carousel_payload_node_restores_original_context() -> None:
    workflow = load_instagram_workflow()
    payload_node = guard.node_by_name(workflow, "Montar Payload Pai Carrossel")
    assert payload_node["parameters"]["mode"] == "runOnceForAllItems"
    js_code = payload_node["parameters"]["jsCode"]

    assert "$('Montar Copy Instagram').first().json" in js_code
    assert "$input.all()" in js_code
    assert "carousel_child_ids" in js_code
    assert "instagram_business_account_id" in js_code
    assert "carousel requires between 2 and 10 child containers" in js_code


def test_prepare_carousel_children_node_expands_multiple_images() -> None:
    workflow = load_instagram_workflow()
    prepare_node = guard.node_by_name(workflow, "Preparar Filhos Carrossel")
    js_code = prepare_node["parameters"]["jsCode"]

    assert "slice(0, 10)" in js_code
    assert "carousel_image_url" in js_code
    assert "carousel requires between 2 and 10 image urls" in js_code


def test_normalize_container_node_accepts_id_or_creation_id() -> None:
    workflow = load_instagram_workflow()
    normalize_node = guard.node_by_name(workflow, "Normalizar Container Criado")
    js_code = normalize_node["parameters"]["jsCode"]

    assert "item.creation_id || item.id" in js_code
    assert "instagram container creation id ausente" in js_code
    assert "creation_id: creationId" in js_code


def test_restore_publish_context_node_keeps_account_and_creation_id() -> None:
    workflow = load_instagram_workflow()
    restore_node = guard.node_by_name(workflow, "Restaurar Contexto Publicacao")
    js_code = restore_node["parameters"]["jsCode"]

    assert "$('Normalizar Container Criado').first().json" in js_code
    assert "instagram_business_account_id: original.instagram_business_account_id" in js_code
    assert "creation_id: original.creation_id" in js_code
    assert "container_status" in js_code
    assert "instagram_graph_container_id" in js_code


def test_validate_instagram_workflow_rejects_process_env_in_code_node() -> None:
    workflow = load_instagram_workflow()
    copy_node = guard.node_by_name(workflow, "Montar Copy Instagram")
    copy_node["parameters"]["jsCode"] = "const x = process.env.INSTAGRAM_WHATSAPP_GROUP_URL;"

    with pytest.raises(guard.InstagramWorkflowGuardError, match="process.env"):
        guard.validate_versioned_workflow(workflow, "OfertasInstagramSupab1")


def test_instagram_publication_event_keeps_dry_run_out_of_dispatch_trigger() -> None:
    workflow = load_instagram_workflow()
    register_node = guard.node_by_name(workflow, "Registrar Resultado Supabase")
    query = register_node["parameters"]["query"]

    assert "case when {{ $json.dry_run ? 'true' : 'false' }} then null" in query
    assert "source_dispatch_plan_id" in query


def test_validate_pin_data_requires_allowlisted_instagram_target() -> None:
    pin_data = guard.build_pin_data(dry_run=True, run_id="test")
    pin_data["Trigger Manual"][0]["json"]["allowed_targets_csv"] = "outro"

    with pytest.raises(guard.InstagramWorkflowGuardError, match="allowlisted"):
        guard.validate_pin_data(pin_data)


def test_instagram_guard_build_update_sql_keeps_workflow_inactive() -> None:
    sql = guard.build_update_sql(
        load_instagram_workflow(),
        "OfertasInstagramSupab1",
        guard.SAFE_PINDATA,
    )

    assert '"pinData"' in sql
    assert '"dry_run":true' in sql
    assert "active = false" in sql
    assert "insert into workflow_entity" in sql
    assert "insert into shared_workflow" in sql
    assert "on conflict (id)" in sql
    assert 'coalesce(workflow_entity."versionCounter", 0) + 1' in sql
    assert "insert into workflow_history" in sql
    assert "autosaved" in sql


def test_instagram_guard_preserves_pindata_when_requested() -> None:
    sql = guard.build_update_sql(
        load_instagram_workflow(),
        "OfertasInstagramSupab1",
        None,
    )

    assert '"pinData" =' not in sql
    assert "active = false" in sql


def test_instagram_real_test_mode_sets_dry_run_false(tmp_path: Path) -> None:
    args = guard.parse_args(["--mode", "instagram-real-test"])
    args.compose_env = tmp_path / "instagram-real.env"
    args.compose_env.write_text(
        "INSTAGRAM_BUSINESS_ACCOUNT_ID=17841400000000000\n"
        "INSTAGRAM_WHATSAPP_GROUP_URL=https://chat.whatsapp.com/FWM9EbDd0eQ7bHxr2iOf9K\n",
        encoding="utf-8",
    )
    config = guard.config_from_args(args)

    payload = config.pin_data["Trigger Manual"][0]["json"]
    assert payload["dry_run"] is False
    assert payload["target"] == "oferta.femininas"
    assert payload["instagram_business_account_id"] == "17841400000000000"
    assert payload["whatsapp_group_url"] == "https://chat.whatsapp.com/FWM9EbDd0eQ7bHxr2iOf9K"


def test_instagram_real_test_mode_requires_business_account_id_in_compose_env(tmp_path: Path) -> None:
    args = guard.parse_args(["--mode", "instagram-real-test"])
    args.compose_env = tmp_path / "instagram-real-missing.env"
    args.compose_env.write_text(
        "INSTAGRAM_WHATSAPP_GROUP_URL=https://chat.whatsapp.com/FWM9EbDd0eQ7bHxr2iOf9K\n",
        encoding="utf-8",
    )

    with pytest.raises(
        guard.InstagramWorkflowGuardError,
        match="INSTAGRAM_BUSINESS_ACCOUNT_ID ausente",
    ):
        guard.config_from_args(args)

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
        node for node in workflow["nodes"] if node["name"] != "Criar Container Pai Carrossel"
    ]

    with pytest.raises(guard.InstagramWorkflowGuardError, match="Criar Container Pai Carrossel"):
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
    assert "case when ctx.dry_run then 'cancelled'" in query
    assert "ready.planned_date <= (now() at time zone 'america/sao_paulo')::date" in query.lower()
    assert "order by ready.planned_date, ready.daily_sequence, ready.instagram_format desc" in query


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


def test_instagram_real_test_mode_sets_dry_run_false() -> None:
    args = guard.parse_args(["--mode", "instagram-real-test"])
    config = guard.config_from_args(args)

    payload = config.pin_data["Trigger Manual"][0]["json"]
    assert payload["dry_run"] is False
    assert payload["target"] == "oferta.femininas"

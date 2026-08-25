from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts/n8n/deploy_test_fanout_workflow_guard.py"
BUILDER_PATH = ROOT / "scripts/n8n/build_test_fanout_workflow.py"
WORKFLOW_PATH = ROOT / "n8n/workflows/ofertas-mvp-supabase-test-fanout.json"


def load_module(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


guard = load_module("deploy_test_fanout_workflow_guard", GUARD_PATH)
builder = load_module("build_test_fanout_workflow", BUILDER_PATH)


def workflow_payload() -> dict[str, object]:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def node(workflow: dict[str, object], name: str) -> dict[str, object]:
    result = guard.node_by_name(workflow, name)
    assert result is not None
    return result


def test_generated_clone_matches_versioned_workflow() -> None:
    assert builder.build() == workflow_payload()


def test_clone_contract_accepts_isolated_fanout() -> None:
    guard.validate_workflow(workflow_payload())


def test_clone_reads_operational_destinations_from_n8n_variables() -> None:
    config = node(workflow_payload(), "Configurar Destinos Fanout Teste")
    code = config["parameters"]["jsCode"]

    assert "$vars[destination.chat_id_var]" in code
    assert "$vars.N8N_TEST_FANOUT_REAL_SEND_ENABLED" in code
    assert "$env" not in code


def test_clone_expansion_restores_fanout_configuration_after_drive_nodes() -> None:
    workflow = workflow_payload()
    for name in (
        "Expandir Destinos Recorrente",
        "Expandir Destinos Estatico",
        "Expandir Destinos Pontual",
    ):
        code = node(workflow, name)["parameters"]["jsCode"]
        assert "$('Configurar Destinos Fanout Teste').first().json" in code
        assert "fanoutConfiguration.real_send_enabled" in code
        assert "destination_count: destinations.length" in code
        assert "destination_count: source.destinations.length" not in code


@pytest.mark.parametrize("forbidden", guard.FORBIDDEN_VALUES)
def test_clone_contract_rejects_production_reference(forbidden: str) -> None:
    workflow = workflow_payload()
    workflow["meta"]["description"] = forbidden

    with pytest.raises(guard.WorkflowGuardError, match="forbidden production value"):
        guard.validate_workflow(workflow)


def test_clone_contract_rejects_ledger_registration() -> None:
    workflow = workflow_payload()
    workflow["meta"]["description"] = "offers.publication_events"

    with pytest.raises(guard.WorkflowGuardError, match="publication_events"):
        guard.validate_workflow(workflow)


def test_clone_contract_rejects_claim_query() -> None:
    workflow = workflow_payload()
    node(workflow, "Validar Contexto")["parameters"]["jsCode"] += "\ndispatch_status = 'claimed'"

    with pytest.raises(guard.WorkflowGuardError, match="claimed"):
        guard.validate_workflow(workflow)


def test_clone_contract_rejects_stale_connection_source() -> None:
    workflow = workflow_payload()
    workflow["connections"]["Validar Allowlist"] = {"main": [[]]}

    with pytest.raises(guard.WorkflowGuardError, match="connection source"):
        guard.validate_workflow(workflow)


def test_clone_contract_rejects_missing_channel_destination() -> None:
    workflow = workflow_payload()
    config = node(workflow, "Configurar Destinos Fanout Teste")
    config["parameters"]["jsCode"] = config["parameters"]["jsCode"].replace(
        "canal-teste-fanout", "canal-removido"
    )

    with pytest.raises(guard.WorkflowGuardError, match="canal-teste-fanout"):
        guard.validate_workflow(workflow)


def test_clone_has_sequential_loop_and_wait_for_each_flow() -> None:
    workflow = workflow_payload()
    expected = {
        "Loop Destinos Recorrente": "Aguardar Intervalo WAHA",
        "Loop Destinos Estatico": "Aguardar Intervalo WAHA Estatico",
        "Loop Destinos Pontual": "Aguardar Intervalo WAHA Pontual",
    }
    for loop_name, wait_name in expected.items():
        assert node(workflow, loop_name)["type"] == "n8n-nodes-base.splitInBatches"
        assert node(workflow, wait_name)["type"] == "n8n-nodes-base.wait"
    assert "Loop Ofertas" in guard.connection_targets(workflow, "Loop Destinos Recorrente")


def test_clone_has_isolated_manual_entries_for_drive_flows() -> None:
    workflow = workflow_payload()
    expected = {
        "Trigger Manual Estatico Fanout Teste": "Resolver Sequencia Estatica",
        "Trigger Manual Pontual Fanout Teste": "Resolver Sequencia Pontual",
    }
    for trigger_name, target_name in expected.items():
        assert node(workflow, trigger_name)["type"] == "n8n-nodes-base.manualTrigger"
        assert target_name in guard.connection_targets(workflow, trigger_name)


def test_clone_has_no_ledger_or_archive_nodes() -> None:
    workflow = workflow_payload()
    names = {item["name"] for item in workflow["nodes"]}
    assert (
        not {
            "Registrar Resultado Supabase",
            "Registrar Resultado Supabase Estatico",
            "Registrar Resultado Supabase Pontual",
        }
        & names
    )
    assert "Mover Pasta msg_XXX Pontual" not in names


def test_guard_update_sql_creates_workflow_history() -> None:
    sql = guard.build_update_sql(workflow_payload(), guard.DEFAULT_WORKFLOW_ID)

    assert "insert into workflow_history" in sql
    assert '"workflowId"' in sql
    assert "active = false" in sql
    assert ")\ninsert into workflow_history" in sql

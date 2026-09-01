# ruff: noqa: E501
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path("scripts/n8n/deploy_instagram_interactions_workflow_guard.py")
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("deploy_instagram_interactions_workflow_guard", MODULE_PATH)
assert SPEC is not None
guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)


def load_workflow() -> dict[str, object]:
    return json.loads(Path("n8n/workflows/ofertas-instagram-interactions-supabase.json").read_text(encoding="utf-8"))


def test_guard_accepts_isolated_versioned_workflow() -> None:
    guard.validate_versioned_workflow(load_workflow(), "OfertasInstagramInteractionsSupab1")


def test_webhook_validation_reads_the_n8n_variable_token() -> None:
    workflow = load_workflow()
    node = guard.node_by_name(workflow, "Validar Challenge Meta")
    code = node["parameters"]["jsCode"]
    assert "$vars.INSTAGRAM_WEBHOOK_VERIFY_TOKEN" in code
    assert "$env.INSTAGRAM_WEBHOOK_VERIFY_TOKEN" not in code


def test_webhook_nodes_have_distinct_stable_ids() -> None:
    workflow = load_workflow()
    get_node = guard.node_by_name(workflow, "Webhook Meta GET")
    post_node = guard.node_by_name(workflow, "Webhook Meta POST")
    assert get_node["webhookId"]
    assert post_node["webhookId"]
    assert get_node["webhookId"] != post_node["webhookId"]


def test_workflow_routes_events_with_compatible_if_nodes() -> None:
    workflow = load_workflow()
    nodes = {node["name"]: node for node in workflow["nodes"]}
    connections = workflow["connections"]

    assert nodes["Roteador Comentario DM Outros"]["type"] == "n8n-nodes-base.if"
    assert nodes["Roteador DM ou Outros"]["type"] == "n8n-nodes-base.if"
    assert all(node["type"] != "n8n-nodes-base.switch" for node in workflow["nodes"])
    assert connections["Roteador Comentario DM Outros"]["main"][0][0]["node"] == "Ignorar Comentario Proprio"
    assert connections["Roteador Comentario DM Outros"]["main"][1][0]["node"] == "Roteador DM ou Outros"
    assert connections["Roteador DM ou Outros"]["main"][0][0]["node"] == "Ignorar DM Propria"
    assert connections["Roteador DM ou Outros"]["main"][1][0]["node"] == "Ignorar Outros Eventos"


def test_workflow_uses_facebook_login_graph_endpoints() -> None:
    workflow = load_workflow()
    request_nodes = [node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.httpRequest"]
    urls = [node["parameters"]["url"] for node in request_nodes]

    assert len(urls) == 3
    assert all("graph.facebook.com/v26.0" in url for url in urls)
    assert not any("graph.instagram.com" in url for url in urls)


def test_guard_rejects_missing_postgres_credential() -> None:
    workflow = load_workflow()
    for node in workflow["nodes"]:
        if node["name"] == "Registrar Comentario Recebido":
            node.pop("credentials")
            break
    with pytest.raises(guard.InstagramInteractionsWorkflowGuardError, match="missing postgres"):
        guard.validate_versioned_workflow(workflow, "OfertasInstagramInteractionsSupab1")


def test_guard_rejects_non_instagram_endpoint() -> None:
    workflow = load_workflow()
    workflow["nodes"].append({"name": "Endpoint externo", "type": "n8n-nodes-base.httpRequest", "parameters": {"url": "https://example.test"}})
    with pytest.raises(guard.InstagramInteractionsWorkflowGuardError, match="forbidden"):
        guard.validate_versioned_workflow(workflow, "OfertasInstagramInteractionsSupab1")


def test_workflow_looks_up_only_published_media_id() -> None:
    workflow = load_workflow()
    node = guard.node_by_name(workflow, "Resolver Publication Event")
    query = node["parameters"]["query"]
    assert "payload ->> 'published_media_id'" in query
    assert "daily_dispatch_plan" not in query
    assert "offer_media_assets" not in query


def test_guard_builds_inactive_workflow_upsert() -> None:
    sql = guard.build_update_sql(load_workflow(), "OfertasInstagramInteractionsSupab1")
    assert "active = false" in sql
    assert "merged_nodes" in sql
    assert "n8n-nodes-base.googleDrive" in sql
    assert "jsonb_set(node, '{credentials}'" in sql
    assert "insert into workflow_history" in sql
    assert "shared_workflow" in sql

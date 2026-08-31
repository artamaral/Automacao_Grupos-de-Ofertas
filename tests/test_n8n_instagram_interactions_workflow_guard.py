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
    assert "insert into workflow_history" in sql
    assert "shared_workflow" in sql

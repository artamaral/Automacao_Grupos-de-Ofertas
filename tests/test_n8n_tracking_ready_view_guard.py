from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/n8n/deploy_tracking_ready_view_guard.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("deploy_tracking_ready_view_guard", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)


@pytest.mark.parametrize(
    ("rollback", "base_refs", "tracked_refs", "expected"),
    [
        (False, 3, 0, "update"),
        (False, 0, 3, "publish"),
        (True, 0, 3, "update"),
        (True, 3, 0, "publish"),
    ],
)
def test_deployment_action_is_idempotent(
    rollback: bool, base_refs: int, tracked_refs: int, expected: str
) -> None:
    assert guard.deployment_action(
        {"base_refs": base_refs, "tracked_refs": tracked_refs}, rollback=rollback
    ) == expected


def test_deployment_action_rejects_mixed_references() -> None:
    with pytest.raises(RuntimeError, match="unexpected workflow view references"):
        guard.deployment_action({"base_refs": 2, "tracked_refs": 1}, rollback=False)


def test_validate_published_workflow_requires_active_version_and_tracked_nodes() -> None:
    version_id = "version-tracked"
    workflow = {
        "active": True,
        "versionId": version_id,
        "activeVersionId": version_id,
        "activeVersion": {
            "nodes": [guard.TRACKED, guard.TRACKED, guard.TRACKED],
        },
    }
    guard.validate_published_workflow(
        workflow, expected_version_id=version_id, rollback=False
    )


def test_validate_published_workflow_rejects_stale_active_version() -> None:
    with pytest.raises(RuntimeError, match="activeVersionId"):
        guard.validate_published_workflow(
            {
                "active": True,
                "versionId": "draft",
                "activeVersionId": "old",
                "activeVersion": {"nodes": [guard.BASE, guard.BASE, guard.BASE]},
            },
            expected_version_id="draft",
            rollback=False,
        )


def test_guard_publishes_through_api_instead_of_updating_active_version_directly() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert '/activate"' in text
    assert 'payload={"versionId": expected_version_id, "expectedChecksum": checksum}' in text
    assert 'set "activeVersionId"' not in text

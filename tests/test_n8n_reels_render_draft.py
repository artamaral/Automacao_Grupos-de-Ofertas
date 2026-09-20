from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "n8n" / "validate_instagram_reels_render_draft.py"
WORKFLOW_PATH = ROOT / "n8n" / "workflows" / "ofertas-instagram-reels-render-draft.json"
SPEC = importlib.util.spec_from_file_location("reels_draft_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def test_versioned_reels_render_draft_preserves_inactive_fallback_contract() -> None:
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))

    validator.validate(workflow)

    assert workflow["active"] is False
    assert workflow["id"] == "OfertasInstagramReelsRenderDraft"

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path("n8n/instagram_webhook_verifier.py")
SPEC = importlib.util.spec_from_file_location("instagram_webhook_verifier", MODULE_PATH)
assert SPEC is not None
verifier = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


TOKEN = "a" * 64


def test_verify_challenge_accepts_matching_subscription() -> None:
    assert verifier.verify_challenge(
        {
            "hub.mode": ["subscribe"],
            "hub.verify_token": [TOKEN],
            "hub.challenge": ["challenge-value"],
        },
        TOKEN,
    ) == "challenge-value"


def test_verify_challenge_rejects_invalid_token() -> None:
    assert verifier.verify_challenge(
        {
            "hub.mode": ["subscribe"],
            "hub.verify_token": ["b" * 64],
            "hub.challenge": ["challenge-value"],
        },
        TOKEN,
    ) is None


def test_verify_challenge_rejects_missing_challenge() -> None:
    assert verifier.verify_challenge(
        {"hub.mode": ["subscribe"], "hub.verify_token": [TOKEN]},
        TOKEN,
    ) is None

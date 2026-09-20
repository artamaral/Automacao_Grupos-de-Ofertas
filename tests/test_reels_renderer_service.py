from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "deploy" / "reels-media" / "renderer_service.py"
SPEC = importlib.util.spec_from_file_location("renderer_service", MODULE_PATH)
assert SPEC and SPEC.loader
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


TEMPLATE = (MODULE_PATH.parent / "templates" / "template_03.ass").read_text(encoding="utf-8")


def test_repeat_ass_replaces_price_and_stops_before_last_frame() -> None:
    generated = renderer.repeat_ass(TEMPLATE, 12.0, "R$ 39,97")

    assert "R$ 39,97" in generated
    assert "R$ XX,XX" not in generated
    assert generated.count("Dialogue:") == 8
    assert "0:00:11.90" in generated


def test_repeat_ass_formats_numeric_price_and_fits_wide_dialogue() -> None:
    generated = renderer.repeat_ass(TEMPLATE, 6.0, "11.75")

    assert "R$ 11,75" in generated
    assert "XX,XX" not in generated
    assert "\\fscx" in generated


def test_repeat_ass_fits_long_template_dialogue_with_compact_break() -> None:
    template = (MODULE_PATH.parent / "templates" / "template_08.ass").read_text(
        encoding="utf-8"
    )

    generated = renderer.repeat_ass(template, 11.04, "79.99")

    dialogue = next(line for line in generated.splitlines() if "Escreva" in line)
    assert r"\N" in dialogue
    assert r"\fscx100" in dialogue
    assert r"\fs109" in dialogue
    assert "Escreva QUERO" in dialogue
    assert r"\Nnos" in dialogue


def test_format_price_accepts_brazilian_and_numeric_values() -> None:
    assert renderer.format_price("11.75") == "R$ 11,75"
    assert renderer.format_price("R$ 1.234,56") == "R$ 1.234,56"


def test_validate_payload_requires_https_and_valid_template() -> None:
    renderer.HOST_ALLOWLIST = {"cdn.example"}
    payload = {
        "job_id": "job-item-1",
        "item_id": "123",
        "planned_date": "2026-09-20",
        "video_url": "https://cdn.example/video.mp4",
        "price": "R$ 39,97",
        "template_id": 3,
        "ass_template": TEMPLATE,
    }

    result = renderer.validate_payload(payload)

    assert result["template_id"] == 3
    assert result["item_id"] == "123"

    payload["video_url"] = "http://cdn.example/video.mp4"
    with pytest.raises(ValueError, match="HTTPS"):
        renderer.validate_payload(payload)


def test_error_message_sanitizes_urls_and_paths() -> None:
    message = renderer.error_message(RuntimeError("GET https://secret.example/a /tmp/private.log"))

    assert "https://" not in message
    assert "secret.example" not in message
    assert "/tmp/private.log" not in message


def test_create_job_is_idempotent_by_job_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class NoopExecutor:
        def submit(self, *_args: object, **_kwargs: object) -> None:
            return None

    renderer.HOST_ALLOWLIST = {"cdn.example"}
    monkeypatch.setattr(renderer, "STATE_ROOT", tmp_path / "state")
    monkeypatch.setattr(renderer, "JOBS_ROOT", tmp_path / "public")
    monkeypatch.setattr(renderer, "_executor", NoopExecutor())
    payload = {
        "job_id": "job-idempotent",
        "item_id": "123",
        "video_url": "https://cdn.example/video.mp4",
        "price": "R$ 39,97",
        "template_id": 1,
        "ass_template": TEMPLATE,
    }

    first = renderer.create_job(payload)
    second = renderer.create_job(payload)

    assert first == second
    payload["price"] = "R$ 40,00"
    with pytest.raises(FileExistsError, match="outro payload"):
        renderer.create_job(payload)

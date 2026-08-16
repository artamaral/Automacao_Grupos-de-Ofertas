from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/n8n/configure_instagram_env_vps.py"
SPEC = importlib.util.spec_from_file_location("configure_instagram_env_vps", MODULE_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def config(*, apply: bool, restart_n8n: bool = False, confirmation: str | None = None):
    return module.UpdateConfig(
        host="hostinger-n8n",
        ssh_bin="ssh",
        remote_env=module.DEFAULT_REMOTE_ENV,
        compose_file=module.DEFAULT_COMPOSE_FILE,
        apply=apply,
        confirmation=confirmation,
        restart_n8n=restart_n8n,
    )


def test_dry_run_only_inspects_remote_env(monkeypatch, capsys) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_run_ssh(_config, command: str, *, payload: str | None = None) -> str:
        calls.append((command, payload))
        return "INSTAGRAM_ACCESS_TOKEN=missing\nINSTAGRAM_BUSINESS_ACCOUNT_ID=missing"

    monkeypatch.setattr(module, "run_ssh", fake_run_ssh)

    assert module.run(config(apply=False)) == 0

    assert len(calls) == 1
    assert calls[0][1] is None
    assert "nenhum segredo foi alterado" in capsys.readouterr().out


def test_apply_requires_explicit_confirmation() -> None:
    with pytest.raises(module.InstagramEnvConfigError, match="deve ser exatamente"):
        module.run(
            config(apply=True),
            access_token="EAA" + "x" * 30,
            business_account_id="17841400000000000",
        )


def test_apply_sends_values_only_through_stdin(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_subprocess_run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs["input"]
        return type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": "UPDATED_ENV mode=600 bytes=100\nN8N_RESTART=OK\n",
                "stderr": "",
            },
        )()

    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)

    assert module.run(
        config(
            apply=True,
            restart_n8n=True,
            confirmation=module.CONFIRMATION,
        ),
        access_token="EAA" + "x" * 30,
        business_account_id="17841400000000000",
    ) == 0

    command_text = " ".join(captured["command"])
    assert "EAA" + "x" * 30 not in command_text
    assert "17841400000000000" not in command_text
    payload = json.loads(captured["input"])
    assert payload["values"]["INSTAGRAM_ACCESS_TOKEN"] == "EAA" + "x" * 30
    assert payload["values"]["INSTAGRAM_BUSINESS_ACCOUNT_ID"] == "17841400000000000"
    assert "EAA" not in capsys.readouterr().out


def test_validate_instagram_values_rejects_malformed_values() -> None:
    with pytest.raises(module.InstagramEnvConfigError, match="curto"):
        module.validate_instagram_values("short", "17841400000000000")
    with pytest.raises(module.InstagramEnvConfigError, match="digitos"):
        module.validate_instagram_values("EAA" + "x" * 30, "abc")


def test_remote_paths_stay_posix() -> None:
    payload = module.build_payload(
        config(apply=True, confirmation=module.CONFIRMATION),
        access_token="EAA" + "x" * 30,
        business_account_id="17841400000000000",
    )

    assert "/opt/automacao_grupo_compras/n8n/.env" in payload
    assert "\\opt\\automacao_grupo_compras" not in payload

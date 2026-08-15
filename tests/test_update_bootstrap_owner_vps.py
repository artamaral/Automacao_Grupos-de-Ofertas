from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts/n8n/update_bootstrap_owner_vps.py"
)
SPEC = importlib.util.spec_from_file_location("update_bootstrap_owner_vps", MODULE_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def config(tmp_path: Path, *, apply: bool, confirmation: str | None = None):
    identity = tmp_path / "id_ed25519"
    identity.write_text("test-key", encoding="utf-8")
    return module.UpdateConfig(
        host="root@example.test",
        identity_file=identity,
        ssh_bin="ssh",
        apply=apply,
        confirmation=confirmation,
        email="owner@example.test",
    )


def test_dry_run_only_inspects_remote_file(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_run_ssh(_config, command: str, *, payload: str | None = None) -> str:
        calls.append((command, payload))
        return "REMOTE_FILE mode=600 owner=root group=root bytes=10"

    monkeypatch.setattr(module, "run_ssh", fake_run_ssh)

    assert module.run(config(tmp_path, apply=False)) == 0
    assert calls == [(module.REMOTE_INSPECT_COMMAND, None)]
    assert "nenhuma credencial foi alterada" in capsys.readouterr().out


def test_apply_requires_explicit_confirmation(tmp_path: Path) -> None:
    with pytest.raises(module.BootstrapOwnerUpdateError, match="deve ser exatamente"):
        module.run(config(tmp_path, apply=True))


def test_apply_sends_password_only_through_stdin(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    captured: dict[str, object] = {}

    def fake_subprocess_run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs["input"]
        return type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": "UPDATED mode=600 owner=root group=root bytes=42\n",
                "stderr": "",
            },
        )()

    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)
    update_config = config(
        tmp_path,
        apply=True,
        confirmation=module.CONFIRMATION,
    )

    assert module.run(
        update_config,
        password="senha-super-secreta",
        password_confirmation="senha-super-secreta",
    ) == 0

    assert "senha-super-secreta" not in " ".join(captured["command"])
    assert captured["input"] == (
        "email=owner@example.test\npassword=senha-super-secreta\n"
    )
    assert "senha-super-secreta" not in capsys.readouterr().out


def test_validate_credentials_rejects_mismatch() -> None:
    with pytest.raises(module.BootstrapOwnerUpdateError, match="nao conferem"):
        module.validate_credentials("owner@example.test", "uma", "outra")


def test_remote_commands_keep_posix_path_on_windows() -> None:
    assert "/opt/automacao_grupo_compras/n8n/bootstrap-owner.txt" in (
        module.REMOTE_INSPECT_COMMAND
    )
    assert "\\opt\\automacao_grupo_compras" not in module.REMOTE_INSPECT_COMMAND

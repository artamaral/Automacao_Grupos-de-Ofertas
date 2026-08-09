from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/n8n/deploy_workflow_guard.py"
SPEC = importlib.util.spec_from_file_location("deploy_workflow_guard", MODULE_PATH)
assert SPEC is not None
guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)


def workflow_payload(
    *,
    url: str = "http://waha:3000/api/sendImage",
    template_text: str = "Resgate o cupom desta página",
) -> dict[str, object]:
    return {
        "id": "OfertasMvpSupab1",
        "nodes": [
            {
                "name": "Montar Mensagens",
                "parameters": {"jsCode": f"const copy = '{template_text}';"},
            },
            {
                "name": "Enviar WhatsApp WAHA",
                "parameters": {"url": url},
            },
        ],
        "connections": {},
        "settings": {},
    }


def test_validate_versioned_workflow_accepts_send_image_template() -> None:
    guard.validate_versioned_workflow(workflow_payload(), "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_send_text() -> None:
    with pytest.raises(guard.WorkflowGuardError, match="forbidden /api/sendText"):
        guard.validate_versioned_workflow(
            workflow_payload(url="http://waha:3000/api/sendText"),
            "OfertasMvpSupab1",
        )


def test_validate_versioned_workflow_rejects_missing_template() -> None:
    with pytest.raises(guard.WorkflowGuardError, match="missing template text"):
        guard.validate_versioned_workflow(
            workflow_payload(template_text="Preco e disponibilidade podem mudar"),
            "OfertasMvpSupab1",
        )


def test_build_update_sql_includes_real_group_pindata_by_default() -> None:
    sql = guard.build_update_sql(
        workflow_payload(),
        "OfertasMvpSupab1",
        guard.REAL_GROUP_PINDATA,
    )

    assert '"pinData"' in sql
    assert '"dry_run":false' in sql
    assert "grupo-ofertas-feminino" in sql
    assert "120363412864266334@g.us" in sql
    assert "active = false" in sql


def test_build_update_sql_preserves_pindata_when_requested() -> None:
    sql = guard.build_update_sql(workflow_payload(), "OfertasMvpSupab1", None)

    assert '"pinData"' not in sql
    assert "active = false" in sql


def test_safe_pindata_uses_dry_run_test_target() -> None:
    args = guard.parse_args(["--safe-pindata"])
    config = guard.config_from_args(args)

    payload = config.pin_data["Trigger Manual"][0]["json"]
    assert payload["dry_run"] is True
    assert payload["target"] == "teste-whatsapp"


def test_preserve_pindata_sets_none() -> None:
    args = guard.parse_args(["--preserve-pindata"])
    config = guard.config_from_args(args)

    assert config.pin_data is None


def test_validate_pin_data_rejects_real_group_without_group_chat_id() -> None:
    pin_data = {
        "Trigger Manual": [
            {
                "json": {
                    "dry_run": False,
                    "target_chat_id": "5511975235421@c.us",
                }
            }
        ]
    }

    with pytest.raises(guard.WorkflowGuardError, match="@g.us"):
        guard.validate_pin_data(pin_data)


def test_validate_deployed_status_rejects_send_text_present() -> None:
    status = {
        "active": False,
        "has_send_image": True,
        "has_send_text": True,
        "has_new_copy": True,
        "pinData": guard.REAL_GROUP_PINDATA,
    }

    with pytest.raises(guard.WorkflowGuardError, match="sendText must be absent"):
        guard.validate_deployed_status(status, guard.REAL_GROUP_PINDATA)

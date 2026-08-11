from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/n8n/deploy_workflow_guard.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("deploy_workflow_guard", MODULE_PATH)
assert SPEC is not None
guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)


def workflow_payload(
    *,
    url: str = "http://waha:3000/api/sendImage",
    template_text: str = guard.EXPECTED_TEMPLATE_CODE_TEXT,
    schedule_cron: str = "0 8-21 * * *",
    schedule_context: str | None = None,
) -> dict[str, object]:
    schedule_context = schedule_context or (
        "return [{ json: { dry_run: false, limit: 3, "
        "target: 'grupo-ofertas-feminino', "
        "target_chat_id: '120363412864266334@g.us', "
        "allowed_targets_csv: 'grupo-ofertas-feminino', "
        "send_delay_seconds_min: 45, send_delay_seconds_max: 90, "
        "run_id: 'schedule-grupo-real' } }];"
    )
    message_layout = guard.EXPECTED_MESSAGE_LAYOUT.replace(
        guard.EXPECTED_TEMPLATE_CODE_TEXT,
        template_text,
    )
    return {
        "id": "OfertasMvpSupab1",
        "nodes": [
            {
                "name": "Schedule Grupo Real",
                "type": "n8n-nodes-base.scheduleTrigger",
                "parameters": {
                    "rule": {
                        "interval": [
                            {"field": "cronExpression", "expression": schedule_cron}
                        ]
                    }
                },
            },
            {
                "name": "Set Contexto Schedule Grupo",
                "type": "n8n-nodes-base.code",
                "parameters": {"jsCode": schedule_context},
            },
            {
                "name": "Montar Mensagens",
                "parameters": {
                    "jsCode": f"const copy = `{message_layout}`;"
                },
            },
            {
                "name": "Enviar WhatsApp WAHA",
                "parameters": {"url": url},
            },
            {
                "name": "Loop Ofertas",
                "type": "n8n-nodes-base.splitInBatches",
                "parameters": {"batchSize": 1},
            },
            {
                "name": "Registrar Resultado Supabase",
                "type": "n8n-nodes-base.postgres",
                "parameters": {},
            },
        ],
        "connections": {
            "Schedule Grupo Real": {
                "main": [
                    [{"node": "Set Contexto Schedule Grupo", "type": "main", "index": 0}]
                ]
            },
            "Set Contexto Schedule Grupo": {
                "main": [[{"node": "Validar Contexto", "type": "main", "index": 0}]]
            },
            "Loop Ofertas": {
                "main": [
                    [],
                    [{"node": "Montar Mensagens", "type": "main", "index": 0}],
                ]
            },
            "Registrar Resultado Supabase": {
                "main": [[{"node": "Loop Ofertas", "type": "main", "index": 0}]]
            },
        },
        "settings": {"timezone": "America/Sao_Paulo"},
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


def test_validate_versioned_workflow_rejects_wrong_schedule_cron() -> None:
    with pytest.raises(guard.WorkflowGuardError, match="cron must include"):
        guard.validate_versioned_workflow(
            workflow_payload(schedule_cron="0 8 * * *"),
            "OfertasMvpSupab1",
        )


def test_validate_versioned_workflow_rejects_safe_schedule_context() -> None:
    with pytest.raises(guard.WorkflowGuardError, match="dry_run: false"):
        guard.validate_versioned_workflow(
            workflow_payload(schedule_context="return [{ json: { dry_run: true } }];"),
            "OfertasMvpSupab1",
        )


def test_validate_versioned_workflow_rejects_missing_emoji_escape() -> None:
    workflow = workflow_payload()
    workflow["nodes"][2]["parameters"]["jsCode"] = (
        "const copy = 'Resgate o cupom desta p\\u{00E1}gina';"
    )

    with pytest.raises(guard.WorkflowGuardError, match="missing emoji escape"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_non_compact_copy_layout() -> None:
    workflow = workflow_payload()
    message_code = workflow["nodes"][2]["parameters"]["jsCode"]
    workflow["nodes"][2]["parameters"]["jsCode"] = message_code.replace(
        "${formatMoney(offer.price)}\n",
        "${formatMoney(offer.price)}\n\n",
    )

    with pytest.raises(guard.WorkflowGuardError, match="compact copy layout"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_processing_on_done_output() -> None:
    workflow = workflow_payload()
    workflow["connections"]["Loop Ofertas"]["main"] = [
        [{"node": "Montar Mensagens", "type": "main", "index": 0}]
    ]

    with pytest.raises(guard.WorkflowGuardError, match="loop output"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_missing_loop_return() -> None:
    workflow = workflow_payload()
    workflow["connections"]["Registrar Resultado Supabase"]["main"] = []

    with pytest.raises(guard.WorkflowGuardError, match="must connect back"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


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
    assert "insert into workflow_history" in sql
    assert "autosaved" in sql


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


def test_mode_teste_telefone_uses_phone_target() -> None:
    args = guard.parse_args(["--mode", "teste-telefone"])
    config = guard.config_from_args(args)

    payload = config.pin_data["Trigger Manual"][0]["json"]
    assert payload["dry_run"] is False
    assert payload["target"] == "5511975235421"
    assert payload["target_chat_id"] == "5511975235421@c.us"


def test_preserve_pindata_sets_none() -> None:
    args = guard.parse_args(["--preserve-pindata"])
    config = guard.config_from_args(args)

    assert config.pin_data is None


def test_validate_pin_data_rejects_real_send_without_supported_chat_id() -> None:
    pin_data = {
        "Trigger Manual": [
            {
                "json": {
                    "dry_run": False,
                    "target_chat_id": "5511975235421",
                }
            }
        ]
    }

    with pytest.raises(guard.WorkflowGuardError, match="@g.us or @c.us"):
        guard.validate_pin_data(pin_data)


def test_validate_deployed_status_rejects_send_text_present() -> None:
    status = {
        "active": False,
        "history_exists": True,
        "has_send_image": True,
        "has_send_text": True,
        "has_new_copy": True,
        "pinData": guard.REAL_GROUP_PINDATA,
    }

    with pytest.raises(guard.WorkflowGuardError, match="sendText must be absent"):
        guard.validate_deployed_status(status, guard.REAL_GROUP_PINDATA)


def test_validate_deployed_status_rejects_missing_version_history() -> None:
    status = {
        "active": False,
        "history_exists": False,
        "has_send_image": True,
        "has_send_text": False,
        "has_new_copy": True,
        "pinData": guard.REAL_GROUP_PINDATA,
    }

    with pytest.raises(guard.WorkflowGuardError, match="workflow_history"):
        guard.validate_deployed_status(status, guard.REAL_GROUP_PINDATA)

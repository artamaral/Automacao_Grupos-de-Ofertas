from __future__ import annotations

import importlib.util
import json
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

WORKFLOW_PATH = Path(__file__).resolve().parents[1] / "n8n/workflows/ofertas-mvp-supabase.json"


def workflow_payload(
    *,
    url: str = "http://waha:3000/api/sendImage",
    template_text: str = guard.EXPECTED_TEMPLATE_CODE_TEXT,
    schedule_cron: str = "0 8-21 * * *",
    schedule_context: str | None = None,
) -> dict[str, object]:
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    legacy_waha = guard.node_by_name(workflow, "Enviar WhatsApp WAHA")
    legacy_schedule = guard.node_by_name(workflow, "Schedule Grupo Real")
    legacy_context = guard.node_by_name(workflow, "Set Contexto Schedule Grupo")
    legacy_message = guard.node_by_name(workflow, "Montar Mensagens")
    assert legacy_waha is not None
    assert legacy_schedule is not None
    assert legacy_context is not None
    assert legacy_message is not None

    legacy_waha["parameters"]["url"] = url
    legacy_schedule["parameters"]["rule"]["interval"][0]["expression"] = schedule_cron
    if schedule_context is not None:
        legacy_context["parameters"]["jsCode"] = schedule_context
    if template_text != guard.EXPECTED_TEMPLATE_CODE_TEXT:
        legacy_message["parameters"]["jsCode"] = legacy_message["parameters"]["jsCode"].replace(
            guard.EXPECTED_TEMPLATE_CODE_TEXT, template_text
        )
    return workflow


def test_validate_versioned_workflow_accepts_send_image_template() -> None:
    guard.validate_versioned_workflow(workflow_payload(), "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_claim_without_ready_filter() -> None:
    workflow = workflow_payload()
    context_node = guard.node_by_name(workflow, "Validar Contexto")
    assert context_node is not None
    context_code = context_node["parameters"]["jsCode"]
    context_node["parameters"]["jsCode"] = context_code.replace(
        "ready.is_ready_for_dispatch",
        "ready.is_not_ready_for_dispatch",
    )

    with pytest.raises(guard.WorkflowGuardError, match="ready.is_ready_for_dispatch"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


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
    message_node = guard.node_by_name(workflow, "Montar Mensagens")
    assert message_node is not None
    message_node["parameters"]["jsCode"] = "const copy = 'Resgate o cupom desta p\\u{00E1}gina';"

    with pytest.raises(guard.WorkflowGuardError, match="missing emoji escape"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_non_compact_copy_layout() -> None:
    workflow = workflow_payload()
    message_node = guard.node_by_name(workflow, "Montar Mensagens")
    assert message_node is not None
    message_code = message_node["parameters"]["jsCode"]
    message_node["parameters"]["jsCode"] = message_code.replace(
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


def test_validate_versioned_workflow_rejects_modified_legacy_node() -> None:
    workflow = workflow_payload()
    legacy_node = guard.node_by_name(workflow, "Trigger Manual")
    assert legacy_node is not None
    legacy_node["notesInFlow"] = True

    with pytest.raises(guard.WorkflowGuardError, match="legacy node modified"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_cross_flow_connection() -> None:
    workflow = workflow_payload()
    workflow["connections"]["Schedule Mensagens Estaticas"]["main"][0].append(
        {"node": "Validar Contexto", "type": "main", "index": 0}
    )

    with pytest.raises(guard.WorkflowGuardError, match="static connections modified"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_second_static_trigger() -> None:
    workflow = workflow_payload()
    workflow["nodes"].append(
        {
            "id": "static-extra-schedule",
            "name": "Schedule Mensagens Estaticas Extra",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [0, 960],
            "parameters": {"rule": {"interval": []}},
        }
    )

    with pytest.raises(guard.WorkflowGuardError, match="exactly one static Schedule"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_changed_static_schedule_crons() -> None:
    workflow = workflow_payload()
    schedule = guard.node_by_name(workflow, "Schedule Mensagens Estaticas")
    assert schedule is not None
    schedule["parameters"]["rule"]["interval"] = [
        {"field": "cronExpression", "expression": "30 9 * * *"},
        {"field": "cronExpression", "expression": "0 11 * * *"},
        {"field": "cronExpression", "expression": "30 14 * * *"},
        {"field": "cronExpression", "expression": "0 16 * * *"},
    ]

    with pytest.raises(guard.WorkflowGuardError, match="static schedule"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_missing_file_route_to_waha() -> None:
    workflow = workflow_payload()
    workflow["connections"]["IF Arquivos Completos"]["main"][1][0]["node"] = (
        "Enviar WhatsApp WAHA Estatico"
    )

    with pytest.raises(guard.WorkflowGuardError, match="static connections modified"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_changed_static_group_id() -> None:
    workflow = workflow_payload()
    resolver = guard.node_by_name(workflow, "Resolver Sequencia Estatica")
    assert resolver is not None
    resolver["parameters"]["jsCode"] = resolver["parameters"]["jsCode"].replace(
        guard.EXPECTED_STATIC_CHAT_ID,
        "120000000000000000@g.us",
    )

    with pytest.raises(guard.WorkflowGuardError, match="target_chat_id"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_google_credential_in_json() -> None:
    workflow = workflow_payload()
    drive_node = guard.node_by_name(workflow, "Buscar Pasta Raiz Drive")
    assert drive_node is not None
    drive_node["credentials"] = {
        "googleDriveOAuth2Api": {"id": "invented", "name": "do-not-version"}
    }

    with pytest.raises(guard.WorkflowGuardError, match="must not be versioned"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_one_shot_removed_1_to_1_step() -> None:
    workflow = workflow_payload()
    workflow["connections"]["Baixar image.jpg Pontual"]["main"] = [
        [{"node": "Montar Upsert Publication Event Pontual", "type": "main", "index": 0}]
    ]

    with pytest.raises(guard.WorkflowGuardError, match="one-shot connections modified"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_one_shot_pending_root_change() -> None:
    workflow = workflow_payload()
    resolver = guard.node_by_name(workflow, "Resolver Sequencia Pontual")
    assert resolver is not None
    resolver["parameters"]["jsCode"] = resolver["parameters"]["jsCode"].replace(
        guard.EXPECTED_ONE_SHOT_ROOT_FOLDER,
        "ofertas-femininas",
    )

    with pytest.raises(guard.WorkflowGuardError, match="ofertas-femininas-pendentes"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_one_shot_archive_root_change() -> None:
    workflow = workflow_payload()
    archive_root = guard.node_by_name(workflow, "Buscar Pasta Enviados Drive Pontual")
    assert archive_root is not None
    archive_root["parameters"]["queryString"] = archive_root["parameters"][
        "queryString"
    ].replace(guard.EXPECTED_ONE_SHOT_ARCHIVE_ROOT_FOLDER, "ofertas-femininas")

    with pytest.raises(guard.WorkflowGuardError, match="ofertas-femininas-enviados"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_one_shot_move_before_supabase() -> None:
    workflow = workflow_payload()
    workflow["connections"]["Registrar Resultado Supabase Pontual"]["main"] = [
        [{"node": "Mover Pasta msg_XXX Pontual", "type": "main", "index": 0}]
    ]

    with pytest.raises(guard.WorkflowGuardError, match="one-shot connections modified"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_one_shot_cancelled_route_to_waha() -> None:
    workflow = workflow_payload()
    workflow["connections"]["IF Arquivos Completos Pontual"]["main"][1][0]["node"] = (
        "Enviar WhatsApp WAHA Pontual"
    )

    with pytest.raises(guard.WorkflowGuardError, match="one-shot connections modified"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_changed_one_shot_schedule_crons() -> None:
    workflow = workflow_payload()
    schedule = guard.node_by_name(workflow, "Schedule Mensagens Pontuais")
    assert schedule is not None
    schedule["parameters"]["rule"]["interval"] = [
        {"field": "cronExpression", "expression": "30 9 * * *"},
        {"field": "cronExpression", "expression": "30 17 * * *"},
    ]

    with pytest.raises(guard.WorkflowGuardError, match="one-shot schedule"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_changed_one_shot_group_id() -> None:
    workflow = workflow_payload()
    resolver = guard.node_by_name(workflow, "Resolver Sequencia Pontual")
    assert resolver is not None
    resolver["parameters"]["jsCode"] = resolver["parameters"]["jsCode"].replace(
        guard.EXPECTED_STATIC_CHAT_ID,
        "120000000000000000@g.us",
    )

    with pytest.raises(guard.WorkflowGuardError, match="target_chat_id"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_changed_one_shot_waha_session() -> None:
    workflow = workflow_payload()
    waha_node = guard.node_by_name(workflow, "Enviar WhatsApp WAHA Pontual")
    assert waha_node is not None
    waha_node["parameters"]["jsonBody"] = waha_node["parameters"]["jsonBody"].replace(
        "session: 'default'",
        "session: 'parallel'",
    )

    with pytest.raises(guard.WorkflowGuardError, match="WAHA payload"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_changed_one_shot_waha_endpoint() -> None:
    workflow = workflow_payload()
    waha_node = guard.node_by_name(workflow, "Enviar WhatsApp WAHA Pontual")
    assert waha_node is not None
    waha_node["parameters"]["url"] = "http://waha:3000/api/sendText"

    with pytest.raises(guard.WorkflowGuardError, match="one-shot WAHA node"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_one_shot_google_credential_in_json() -> None:
    workflow = workflow_payload()
    drive_node = guard.node_by_name(workflow, "Buscar Pasta Enviados Drive Pontual")
    assert drive_node is not None
    drive_node["credentials"] = {
        "googleDriveOAuth2Api": {"id": "invented", "name": "do-not-version"}
    }

    with pytest.raises(guard.WorkflowGuardError, match="must not be versioned"):
        guard.validate_versioned_workflow(workflow, "OfertasMvpSupab1")


def test_validate_versioned_workflow_rejects_active_json() -> None:
    workflow = workflow_payload()
    workflow["active"] = True

    with pytest.raises(guard.WorkflowGuardError, match="active must be false"):
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

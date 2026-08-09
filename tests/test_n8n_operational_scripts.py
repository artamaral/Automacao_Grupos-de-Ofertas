from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts/n8n"
sys.path.insert(0, str(SCRIPT_DIR))


def load_script(name: str):
    path = SCRIPT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ops_common = load_script("ops_common")
check_last_execution = load_script("check_last_execution")
run_workflow_manual = load_script("run_workflow_manual")


def test_operation_modes_define_expected_pindata() -> None:
    real_group = ops_common.resolve_mode("grupo-real")
    phone = ops_common.resolve_mode("teste-telefone")
    dry_run = ops_common.resolve_mode("dry-run")
    preserve = ops_common.resolve_mode("preserve-pindata")

    assert real_group.pin_data["Trigger Manual"][0]["json"]["target_chat_id"].endswith("@g.us")
    assert phone.pin_data["Trigger Manual"][0]["json"]["target_chat_id"].endswith("@c.us")
    assert dry_run.pin_data["Trigger Manual"][0]["json"]["dry_run"] is True
    assert preserve.pin_data is None


def test_run_workflow_manual_requires_explicit_mode() -> None:
    with pytest.raises(SystemExit):
        run_workflow_manual.parse_args([])


def test_run_workflow_manual_rejects_preserve_pindata() -> None:
    assert "preserve-pindata" not in run_workflow_manual.parse_args(["--mode", "grupo-real"]).mode
    with pytest.raises(SystemExit):
        run_workflow_manual.parse_args(["--mode", "preserve-pindata"])


def test_decode_referenced_json_resolves_n8n_execution_data() -> None:
    encoded = json.dumps(
        [
            {"resultData": "1"},
            {"runData": "2"},
            {"Montar Mensagens": "3"},
            [{"data": "4"}],
            {"main": "5"},
            [[{"json": "6"}]],
            {"message_text": "7"},
            "copy teste",
        ]
    )

    decoded = ops_common.decode_referenced_json(encoded)

    assert decoded["resultData"]["runData"]["Montar Mensagens"][0]["data"]["main"][0][0][
        "json"
    ]["message_text"] == "copy teste"


def test_check_last_execution_detects_send_image_and_new_copy() -> None:
    payload = {
        "id": 42,
        "status": "success",
        "mode": "manual",
        "startedAt": "2026-08-09T21:49:45Z",
        "stoppedAt": "2026-08-09T21:49:50Z",
        "workflowVersionId": "version-1",
        "workflowData": {"nodes": [{"parameters": {"url": "http://waha:3000/api/sendImage"}}]},
        "data": json.dumps(
            [
                {"resultData": "1"},
                {"runData": "2"},
                {
                    "Montar Mensagens": "3",
                    "Normalizar Resultado WAHA": "8",
                    "Registrar Resultado Supabase": "12",
                },
                [{"data": "4"}],
                {"main": "5"},
                [[{"json": "6"}]],
                {
                    "message_text": "7",
                    "product_name": "Produto A",
                    "target": "grupo-ofertas-feminino",
                },
                "🔥 Produto A\n\n🎟️ Resgate o cupom desta página:\nhttps://example.test",
                [{"data": "9"}],
                {"main": "10"},
                [[{"json": "11"}]],
                {
                    "delivery_status": "confirmed",
                    "send_result": "sent_to_adapter",
                    "adapter_response_type": "image",
                    "adapter_status": "sent_to_adapter",
                    "message_text": "7",
                    "image_url": "https://example.test/image.jpg",
                },
                [{"data": "13"}],
                {"main": "14"},
                [[{"json": "15"}]],
                {"publish_id": "pub-1"},
            ]
        ),
    }

    summary = check_last_execution.build_summary(payload, copy_chars=80)

    assert summary.endpoint == "sendImage"
    assert summary.copy_template == "novo"
    assert summary.publish_id == "pub-1"
    check_last_execution.validate_summary(summary, expect_real_image=True)


def test_check_last_execution_fails_on_old_copy_and_send_text() -> None:
    summary = check_last_execution.ExecutionSummary(
        execution_id=1,
        status="success",
        mode="manual",
        started_at=None,
        stopped_at=None,
        workflow_version_id="old",
        endpoint="sendText",
        publish_id="pub-1",
        delivery_status="confirmed",
        send_result="sent_to_adapter",
        adapter_response_type="chat",
        adapter_status="sent_to_adapter",
        product_name="Produto",
        target="grupo",
        image_url=None,
        copy_template="antigo",
        copy_excerpt="Aviso: este link pode gerar comissao de afiliado.",
    )

    with pytest.raises(check_last_execution.LastExecutionError, match="sendText"):
        check_last_execution.validate_summary(summary, expect_real_image=True)

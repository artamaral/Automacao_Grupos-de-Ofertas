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
run_operational_round = load_script("run_operational_round")


def test_operation_modes_define_expected_pindata() -> None:
    real_group = ops_common.resolve_mode("grupo-real")
    phone = ops_common.resolve_mode("teste-telefone")
    dry_run = ops_common.resolve_mode("dry-run")
    preserve = ops_common.resolve_mode("preserve-pindata")

    assert real_group.pin_data["Trigger Manual"][0]["json"]["target_chat_id"].endswith("@g.us")
    assert real_group.pin_data["Trigger Manual"][0]["json"]["limit"] == 3
    assert real_group.pin_data["Trigger Manual"][0]["json"]["send_delay_seconds_min"] == 45
    assert real_group.pin_data["Trigger Manual"][0]["json"]["send_delay_seconds_max"] == 90
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


def test_run_operational_round_requires_explicit_mode() -> None:
    with pytest.raises(SystemExit):
        run_operational_round.parse_args([])


def test_run_operational_round_accepts_only_operational_modes() -> None:
    assert run_operational_round.parse_args(["--mode", "grupo-real"]).mode == "grupo-real"
    assert run_operational_round.parse_args(["--mode", "teste-telefone"]).mode == "teste-telefone"
    assert run_operational_round.parse_args(["--mode", "dry-run"]).mode == "dry-run"
    with pytest.raises(SystemExit):
        run_operational_round.parse_args(["--mode", "preserve-pindata"])


def test_run_operational_round_check_args_require_real_image_for_real_modes() -> None:
    run_output = "INFO | execution_id=123\n"

    assert run_operational_round.check_args("grupo-real", run_output) == [
        "--execution-id",
        "123",
        "--expect-real-image",
    ]
    assert run_operational_round.check_args("teste-telefone", run_output) == [
        "--execution-id",
        "123",
        "--expect-real-image",
    ]
    assert run_operational_round.check_args("dry-run", run_output) == [
        "--execution-id",
        "123",
    ]


def test_run_operational_round_sanitizes_sensitive_output() -> None:
    output = run_operational_round.sanitize_text(
        "INFO | ok=true\nX-Api-Key: segredo\npassword=segredo\nplain token leaked"
    )

    assert "segredo" not in output
    assert "plain token leaked" not in output
    assert "X-Api-Key: <redacted>" in output
    assert "password=<redacted>" in output


def test_run_operational_round_stops_on_first_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_step(name: str, args: list[str]):
        calls.append((name, args))
        if name == "run_workflow_manual.py":
            raise run_operational_round.OperationalRoundError("falhou")
        return run_operational_round.StepResult(name, "", "", 0)

    monkeypatch.setattr(run_operational_round, "run_step", fake_run_step)

    with pytest.raises(run_operational_round.OperationalRoundError):
        run_operational_round.run(run_operational_round.RoundConfig("teste-telefone"))

    assert calls == [
        ("deploy_workflow_guard.py", ["--mode", "teste-telefone"]),
        ("run_workflow_manual.py", ["--mode", "teste-telefone"]),
    ]


def test_run_operational_round_prints_final_summary(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_step(name: str, args: list[str]):
        calls.append((name, args))
        if name == "run_workflow_manual.py":
            return run_operational_round.StepResult(name, "INFO | execution_id=456\n", "", 0)
        return run_operational_round.StepResult(name, "", "", 0)

    def fake_run_check_with_retry(args: list[str]):
        calls.append(("check_last_execution.py", args))
        return run_operational_round.StepResult(
            "check_last_execution.py",
            "\n".join(
                [
                    "INFO | execution_id=456",
                    "INFO | endpoint=sendImage",
                    "INFO | publish_id=pub-456",
                    "INFO | delivery_status=confirmed",
                    "INFO | adapter_response_type=image",
                    "INFO | copy_template=novo",
                ]
            ),
            "",
            0,
        )

    monkeypatch.setattr(run_operational_round, "run_step", fake_run_step)
    monkeypatch.setattr(run_operational_round, "run_check_with_retry", fake_run_check_with_retry)

    assert run_operational_round.run(run_operational_round.RoundConfig("teste-telefone")) == 0

    assert calls == [
        ("deploy_workflow_guard.py", ["--mode", "teste-telefone"]),
        ("run_workflow_manual.py", ["--mode", "teste-telefone"]),
        (
            "check_last_execution.py",
            ["--execution-id", "456", "--expect-real-image"],
        ),
    ]
    output = capsys.readouterr().out
    assert "INFO | resumo_final=true" in output
    assert "INFO | execution_id=456" in output
    assert "INFO | adapter_response_type=image" in output


def test_run_operational_round_retries_check(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    attempts: list[list[str]] = []

    def fake_execute_step(name: str, args: list[str]):
        attempts.append(args)
        if len(attempts) == 1:
            return run_operational_round.StepResult(name, "", "ERRO | incompleto", 1)
        return run_operational_round.StepResult(name, "INFO | execution_id=1\n", "", 0)

    monkeypatch.setattr(run_operational_round, "execute_step", fake_execute_step)
    monkeypatch.setattr(run_operational_round.time, "sleep", lambda _seconds: None)

    result = run_operational_round.run_check_with_retry(["--execution-id", "1"])

    assert result.returncode == 0
    assert attempts == [["--execution-id", "1"], ["--execution-id", "1"]]
    assert "check_last_execution_retry=1/" in capsys.readouterr().out


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
                "Produto A\n\nResgate o cupom desta p\u00e1gina:\nhttps://example.test",
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

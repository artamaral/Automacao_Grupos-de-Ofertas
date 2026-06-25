import json

from ofertas_bot.local_review_bundle_cli import run


def write_json(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_local_review_bundle_cli_saves_valid_bundle(tmp_path, capsys) -> None:
    queue_path = tmp_path / "review_queue.json"
    approved_path = tmp_path / "approved_messages.json"
    manifest_path = tmp_path / "publication_manifest.json"
    artifact_path = tmp_path / "dispatch_artifact.json"
    report_path = tmp_path / "dispatch_report.json"
    bundle_path = tmp_path / "bundle.json"
    write_json(queue_path, [{"status": "approved"}])
    write_json(approved_path, [{"draft": {"text": "ok"}}])
    write_json(manifest_path, [{"status": "ready", "target": "grupo"}])
    write_json(
        artifact_path,
        {
            "generated_at": "2026-06-25T23:00:00-03:00",
            "timezone": "America/Sao_Paulo",
            "summary": {
                "total_available_messages": 1,
                "total_selected_messages": 1,
            },
            "targets": [
                {
                    "target": "grupo",
                    "adapter_kind": "whatsapp",
                    "message_count": 1,
                }
            ],
        },
    )
    write_json(
        report_path,
        {
            "source_generated_at": "2026-06-25T23:00:00-03:00",
            "source_timezone": "America/Sao_Paulo",
            "summary": {
                "total_messages": 1,
                "total_selected_messages": 1,
            },
            "targets": [
                {
                    "target": "grupo",
                    "adapter_kind": "whatsapp",
                    "message_count": 1,
                }
            ],
        },
    )

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--approved-messages-json",
            str(approved_path),
            "--manifest-json",
            str(manifest_path),
            "--dispatch-artifact-json",
            str(artifact_path),
            "--dispatch-report-json",
            str(report_path),
            "--save-bundle-json",
            str(bundle_path),
        ]
    )

    output = capsys.readouterr().out
    report = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert report["valid"] is True
    assert report["checks"]["queue_pending"] == 0
    assert report["checks"]["approved_messages"] == 1
    assert report["checks"]["manifest_ready"] == 1
    assert report["checks"]["dispatch_targets"] == 1
    assert report["checks"]["dispatch_report_messages"] == 1
    assert "Nenhum envio" in output


def test_local_review_bundle_cli_blocks_pending_queue(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    approved_path = tmp_path / "approved_messages.json"
    manifest_path = tmp_path / "publication_manifest.json"
    artifact_path = tmp_path / "dispatch_artifact.json"
    report_path = tmp_path / "dispatch_report.json"
    bundle_path = tmp_path / "bundle.json"
    write_json(queue_path, [{"status": "pending"}])
    write_json(approved_path, [{"draft": {"text": "ok"}}])
    write_json(manifest_path, [{"status": "ready", "target": "grupo"}])
    write_json(
        artifact_path,
        {
            "generated_at": "2026-06-25T23:00:00-03:00",
            "timezone": "America/Sao_Paulo",
            "summary": {
                "total_available_messages": 1,
                "total_selected_messages": 1,
            },
            "targets": [{"target": "grupo", "adapter_kind": "whatsapp", "message_count": 1}],
        },
    )
    write_json(
        report_path,
        {
            "source_generated_at": "2026-06-25T23:00:00-03:00",
            "source_timezone": "America/Sao_Paulo",
            "summary": {
                "total_messages": 1,
                "total_selected_messages": 1,
            },
            "targets": [{"target": "grupo", "adapter_kind": "whatsapp", "message_count": 1}],
        },
    )

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--approved-messages-json",
            str(approved_path),
            "--manifest-json",
            str(manifest_path),
            "--dispatch-artifact-json",
            str(artifact_path),
            "--dispatch-report-json",
            str(report_path),
            "--save-bundle-json",
            str(bundle_path),
        ]
    )

    report = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert exit_code == 3
    assert report["valid"] is False
    assert "fila ainda possui itens pendentes" in report["issues"]


def test_local_review_bundle_cli_blocks_dispatch_mismatch(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    approved_path = tmp_path / "approved_messages.json"
    manifest_path = tmp_path / "publication_manifest.json"
    artifact_path = tmp_path / "dispatch_artifact.json"
    report_path = tmp_path / "dispatch_report.json"
    bundle_path = tmp_path / "bundle.json"
    write_json(queue_path, [{"status": "approved"}])
    write_json(approved_path, [{"draft": {"text": "ok"}}])
    write_json(manifest_path, [{"status": "ready", "target": "grupo"}])
    write_json(
        artifact_path,
        {
            "generated_at": "2026-06-25T23:00:00-03:00",
            "timezone": "America/Sao_Paulo",
            "summary": {
                "total_available_messages": 1,
                "total_selected_messages": 1,
            },
            "targets": [{"target": "grupo", "adapter_kind": "whatsapp", "message_count": 1}],
        },
    )
    write_json(
        report_path,
        {
            "source_generated_at": "2026-06-25T23:10:00-03:00",
            "source_timezone": "America/Sao_Paulo",
            "summary": {
                "total_messages": 2,
                "total_selected_messages": 2,
            },
            "targets": [{"target": "grupo", "adapter_kind": "whatsapp", "message_count": 2}],
        },
    )

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--approved-messages-json",
            str(approved_path),
            "--manifest-json",
            str(manifest_path),
            "--dispatch-artifact-json",
            str(artifact_path),
            "--dispatch-report-json",
            str(report_path),
            "--save-bundle-json",
            str(bundle_path),
        ]
    )

    report = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert exit_code == 3
    assert report["valid"] is False
    assert "dispatch artifact e dispatch report divergem em mensagens da rodada" in report["issues"]

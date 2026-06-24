import json

from ofertas_bot.local_artifacts_doctor_cli import run


def write_json(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_local_artifacts_doctor_cli_accepts_valid_artifacts(tmp_path, capsys) -> None:
    queue_path = tmp_path / "review_queue.json"
    approved_path = tmp_path / "approved_messages.json"
    manifest_path = tmp_path / "manifest.json"
    bundle_path = tmp_path / "bundle.json"
    write_json(queue_path, [{"status": "approved"}])
    write_json(approved_path, [{"draft": {"text": "ok"}}])
    write_json(manifest_path, [{"status": "ready"}])
    write_json(bundle_path, {"valid": True})

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--approved-json",
            str(approved_path),
            "--manifest-json",
            str(manifest_path),
            "--bundle-json",
            str(bundle_path),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Doctor local aprovado" in output
    assert "Nenhum envio" in output


def test_local_artifacts_doctor_cli_blocks_pending_queue(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    approved_path = tmp_path / "approved_messages.json"
    manifest_path = tmp_path / "manifest.json"
    write_json(queue_path, [{"status": "pending"}])
    write_json(approved_path, [{"draft": {"text": "ok"}}])
    write_json(manifest_path, [{"status": "ready"}])

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--approved-json",
            str(approved_path),
            "--manifest-json",
            str(manifest_path),
        ]
    )

    assert exit_code == 3

import json

from ofertas_bot.local_review_bundle_cli import run


def write_json(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_local_review_bundle_cli_saves_valid_bundle(tmp_path, capsys) -> None:
    queue_path = tmp_path / "review_queue.json"
    approved_path = tmp_path / "approved_messages.json"
    manifest_path = tmp_path / "publication_manifest.json"
    bundle_path = tmp_path / "bundle.json"
    write_json(queue_path, [{"status": "approved"}])
    write_json(approved_path, [{"draft": {"text": "ok"}}])
    write_json(manifest_path, [{"status": "ready", "target": "grupo"}])

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--approved-messages-json",
            str(approved_path),
            "--manifest-json",
            str(manifest_path),
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
    assert "Nenhum envio" in output


def test_local_review_bundle_cli_blocks_pending_queue(tmp_path) -> None:
    queue_path = tmp_path / "review_queue.json"
    approved_path = tmp_path / "approved_messages.json"
    manifest_path = tmp_path / "publication_manifest.json"
    bundle_path = tmp_path / "bundle.json"
    write_json(queue_path, [{"status": "pending"}])
    write_json(approved_path, [{"draft": {"text": "ok"}}])
    write_json(manifest_path, [{"status": "ready", "target": "grupo"}])

    exit_code = run(
        [
            "--queue-json",
            str(queue_path),
            "--approved-messages-json",
            str(approved_path),
            "--manifest-json",
            str(manifest_path),
            "--save-bundle-json",
            str(bundle_path),
        ]
    )

    report = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert exit_code == 3
    assert report["valid"] is False
    assert "fila ainda possui itens pendentes" in report["issues"]

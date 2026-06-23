import hashlib
import json

from ofertas_bot.local_manifest_audit_cli import run


def test_local_manifest_audit_cli_prints_and_saves_report(tmp_path, capsys) -> None:
    file_path = tmp_path / "manifest.json"
    audit_path = tmp_path / "audit.json"
    payload = [
        {
            "status": "ready",
            "target": "grupo-maquiagem",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    content = json.dumps(payload).encode("utf-8")
    file_path.write_bytes(content)

    exit_code = run(
        [
            "--file",
            str(file_path),
            "--save-audit-json",
            str(audit_path),
        ]
    )

    output = capsys.readouterr().out
    report = json.loads(audit_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert report["sha256"] == hashlib.sha256(content).hexdigest()
    assert report["size_bytes"] == len(content)
    assert report["status_counts"] == {"ready": 1}
    assert report["valid"] is True
    assert "Nenhum envio" in output


def test_local_manifest_audit_cli_blocks_empty_list(tmp_path) -> None:
    file_path = tmp_path / "manifest.json"
    file_path.write_text("[]", encoding="utf-8")

    exit_code = run(["--file", str(file_path)])

    assert exit_code == 3

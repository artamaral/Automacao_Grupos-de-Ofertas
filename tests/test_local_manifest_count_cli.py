import json

from ofertas_bot.local_manifest_count_cli import run


def test_local_manifest_count_cli_prints_status_counts(tmp_path, capsys) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            [
                {"status": "ready"},
                {"status": "ready"},
                {"status": "blocked"},
            ]
        ),
        encoding="utf-8",
    )

    exit_code = run(["--manifest-json", str(manifest_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Total: 3" in output
    assert "ready: 2" in output
    assert "blocked: 1" in output
    assert "Nenhum envio" in output

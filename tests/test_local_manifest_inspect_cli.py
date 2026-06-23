import json

from ofertas_bot.local_manifest_inspect_cli import run


def test_local_manifest_inspect_cli_prints_items(tmp_path, capsys) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "status": "ready",
                    "target": "grupo-maquiagem",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "draft": {
                        "offer": {
                            "marketplace": "mock",
                            "niche": "maquiagem",
                            "price": 49.9,
                            "title": "Kit Maquiagem",
                        }
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = run(["--manifest-json", str(manifest_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "ITEM | 1 | status=ready" in output
    assert "target=grupo-maquiagem" in output
    assert "marketplace=mock" in output
    assert "niche=maquiagem" in output
    assert "Kit Maquiagem" in output
    assert "Nenhum envio" in output


def test_local_manifest_inspect_cli_handles_empty_manifest(tmp_path, capsys) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("[]", encoding="utf-8")

    exit_code = run(["--manifest-json", str(manifest_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Manifesto local vazio" in output

import json

from ofertas_bot import harness


def test_harness_saves_normalized_offers_when_requested(tmp_path) -> None:
    output_path = tmp_path / "offers.json"

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--save-json",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert len(payload) == 1
    assert payload[0]["marketplace"] == "mock"
    assert payload[0]["niche"] == "maquiagem"
    assert payload[0]["title"]
    assert payload[0]["url"]
    assert "price" in payload[0]


def test_harness_does_not_save_json_by_default(tmp_path) -> None:
    output_path = tmp_path / "offers.json"

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
        ]
    )

    assert exit_code == 0
    assert not output_path.exists()


def test_harness_handles_save_json_write_error(tmp_path, capsys) -> None:
    output_path = tmp_path

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--save-json",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Não foi possível salvar o JSON de ofertas" in captured.err
    assert "AÇÃO | Verifique se o caminho é um arquivo válido" in captured.err


def test_harness_saves_copy_briefs_when_requested(tmp_path) -> None:
    output_path = tmp_path / "copy_briefs.json"

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--save-copy-briefs-json",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert len(payload) == 1
    assert payload[0]["content_type"] == "product_offer"
    assert payload[0]["facts"]["niche"] == "maquiagem"
    assert "score" in payload[0]["selection"]
    assert payload[0]["selection"]["reasons"]
    assert payload[0]["required_disclosures"]
    assert payload[0]["copy_constraints"]

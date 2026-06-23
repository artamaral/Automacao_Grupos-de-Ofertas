import json

from ofertas_bot.tools import anonymize_payload


def test_anonymize_payload_tool_writes_sanitized_json(tmp_path, capsys) -> None:
    input_path = tmp_path / "raw.json"
    output_path = tmp_path / "safe.json"
    input_path.write_text(
        json.dumps(
            {
                "sign": "abc123",
                "item_url": "https://marketplace.example/item/123",
                "item_name": "Produto real",
            }
        ),
        encoding="utf-8",
    )

    exit_code = anonymize_payload.run(
        ["--input", str(input_path), "--output", str(output_path)]
    )

    captured = capsys.readouterr()
    saved_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert saved_payload == {
        "sign": "<redacted>",
        "item_url": "https://example.com/redacted",
        "item_name": "Produto anonimizado",
    }
    assert "INFO | Payload anonimizado salvo" in captured.out


def test_anonymize_payload_tool_rejects_same_input_and_output(tmp_path, capsys) -> None:
    input_path = tmp_path / "raw.json"
    input_path.write_text("{}", encoding="utf-8")

    exit_code = anonymize_payload.run(
        ["--input", str(input_path), "--output", str(input_path)]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Entrada e saída não podem ser o mesmo arquivo" in captured.err

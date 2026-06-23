import json

from ofertas_bot.tools import capture_shopee_payload


class FakeShopeeProvider:
    def __init__(self, settings) -> None:
        self.settings = settings

    def fetch_raw_response(self, niche: str, limit: int):
        return {
            "items": [
                {
                    "title": "Oferta sensível",
                    "url": "https://example.com/oferta",
                    "image_url": "https://example.com/imagem.jpg",
                    "seller_id": "seller-123",
                    "sign": "signature-value",
                }
            ],
            "meta": {"keyword": niche, "limit": limit},
        }


def test_capture_shopee_payload_saves_anonymized_response(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SHOPEE_SEARCH_PATH_CONFIRMED", "true")
    monkeypatch.setattr(capture_shopee_payload, "ShopeeProvider", FakeShopeeProvider)

    exit_code = capture_shopee_payload.run(
        ["--niche", "maquiagem", "--limit", "1", "--output", "tmp/out.json"]
    )

    payload = json.loads(tmp_path.joinpath("tmp/out.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["items"][0]["title"] == "Produto anonimizado"
    assert payload["items"][0]["url"] == "https://example.com/redacted"
    assert payload["items"][0]["image_url"] == "https://example.com/redacted"
    assert payload["items"][0]["seller_id"] == "<redacted>"
    assert payload["items"][0]["sign"] == "<redacted>"


def test_capture_shopee_payload_blocks_unconfirmed_endpoint(monkeypatch, capsys) -> None:
    monkeypatch.delenv("SHOPEE_SEARCH_PATH_CONFIRMED", raising=False)

    exit_code = capture_shopee_payload.run(["--niche", "maquiagem"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Endpoint da Shopee não confirmado" in captured.err


def test_capture_shopee_payload_requires_tmp_output() -> None:
    try:
        capture_shopee_payload.run(
            ["--niche", "maquiagem", "--output", "tests/fixtures/out.json"]
        )
    except SystemExit as error:
        assert str(error) == "ERRO | O arquivo de saída deve ficar dentro de tmp/"
    else:
        raise AssertionError("expected SystemExit")

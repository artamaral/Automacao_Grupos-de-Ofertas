import json

from ofertas_bot.tools import capture_shopee_payload


class FakeShopeeProvider:
    def __init__(self, settings) -> None:
        self.settings = settings

    def fetch_raw_response(self, niche: str, limit: int):
        return {
            "data": {
                "shopeeOfferV2": {
                    "nodes": [
                        {
                            "offerName": "Oferta sensivel",
                            "offerLink": "https://example.com/oferta",
                            "imageUrl": "https://example.com/imagem.jpg",
                            "seller_id": "seller-123",
                            "signature": "signature-value",
                        }
                    ],
                    "pageInfo": {"page": 1, "limit": limit, "hasNextPage": False},
                }
            },
            "meta": {"keyword": niche, "limit": limit},
        }


def test_capture_shopee_payload_saves_anonymized_response(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(capture_shopee_payload, "ShopeeProvider", FakeShopeeProvider)

    exit_code = capture_shopee_payload.run(
        ["--niche", "maquiagem", "--limit", "1", "--output", "tmp/out.json"]
    )

    payload = json.loads(tmp_path.joinpath("tmp/out.json").read_text(encoding="utf-8"))
    node = payload["data"]["shopeeOfferV2"]["nodes"][0]
    assert exit_code == 0
    assert node["offerName"] == "Oferta sensivel"
    assert node["offerLink"] == "https://example.com/redacted"
    assert node["imageUrl"] == "https://example.com/redacted"
    assert node["seller_id"] == "<redacted>"
    assert node["signature"] == "<redacted>"


def test_capture_shopee_payload_saves_public_response_mode(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(capture_shopee_payload, "ShopeeProvider", FakeShopeeProvider)

    exit_code = capture_shopee_payload.run(
        ["--niche", "maquiagem", "--limit", "1", "--output", "tmp/out.json", "--mode", "public"]
    )

    payload = json.loads(tmp_path.joinpath("tmp/out.json").read_text(encoding="utf-8"))
    node = payload["data"]["shopeeOfferV2"]["nodes"][0]
    assert exit_code == 0
    assert node["offerName"] == "Oferta sensivel"
    assert node["offerLink"] == "https://example.com/oferta"
    assert node["imageUrl"] == "https://example.com/imagem.jpg"
    assert node["seller_id"] == "<redacted>"
    assert node["signature"] == "<redacted>"


def test_capture_shopee_payload_requires_tmp_output() -> None:
    try:
        capture_shopee_payload.run(
            ["--niche", "maquiagem", "--output", "tests/fixtures/out.json"]
        )
    except SystemExit as error:
        assert str(error) == "ERRO | O arquivo de saida deve ficar dentro de tmp/"
    else:
        raise AssertionError("expected SystemExit")

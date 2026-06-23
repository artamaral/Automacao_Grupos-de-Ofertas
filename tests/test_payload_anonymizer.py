from ofertas_bot.providers.payload_anonymizer import anonymize_payload


def test_anonymize_payload_redacts_sensitive_fields() -> None:
    raw_payload = {
        "sign": "abc123",
        "access_token": "secret-token",
        "item_name": "Produto real",
        "item_url": "https://marketplace.example/item/123",
        "image_url": "https://marketplace.example/image.jpg",
        "seller_id": 123456,
        "items": [
            {
                "product_name": "Outro produto real",
                "shop_name": "Loja real",
                "price": 49.9,
            }
        ],
    }

    anonymized = anonymize_payload(raw_payload)

    assert anonymized["sign"] == "<redacted>"
    assert anonymized["access_token"] == "<redacted>"
    assert anonymized["item_name"] == "Produto anonimizado"
    assert anonymized["item_url"] == "https://example.com/redacted"
    assert anonymized["image_url"] == "https://example.com/redacted"
    assert anonymized["seller_id"] == "<redacted>"
    assert anonymized["items"][0]["product_name"] == "Produto anonimizado"
    assert anonymized["items"][0]["shop_name"] == "<redacted>"
    assert anonymized["items"][0]["price"] == 49.9

from ofertas_bot import harness
from ofertas_bot.settings import Settings


def make_shopee_settings(enabled: bool = True) -> Settings:
    values = {
        "enable_real_http": enabled,
        "shopee_partner_id": "123456789",
        "shopee_tracking_id": "tracking",
    }
    values["shopee_" + "secret_key"] = "credential"
    return Settings(**values)


def test_harness_prints_safe_shopee_request_preview(monkeypatch, capsys) -> None:
    monkeypatch.setattr(harness, "get_settings", make_shopee_settings)
    monkeypatch.setattr(harness, "time", lambda: 1234567890)
    monkeypatch.setenv("SHOPEE_BASE_URL", "https://api.shopee.test")

    exit_code = harness.run(
        [
            "--marketplace",
            "shopee",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--print-provider-request",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "INFO | Preview seguro do request da Shopee" in captured.out
    assert "INFO | method=GET" in captured.out
    assert "INFO | url=https://api.shopee.test" in captured.out
    assert "INFO | param.keyword=maquiagem" in captured.out
    assert "INFO | param.page_size=1" in captured.out
    assert "INFO | param.timestamp=1234567890" in captured.out
    assert "INFO | param.partner_id=<masked:9 chars>" in captured.out
    assert "INFO | param.sign=<masked:64 chars>" in captured.out
    assert "123456789" not in captured.out
    assert "INFO | Nenhuma chamada HTTP foi executada." in captured.out
    assert "INFO | Nenhuma publicação foi executada." in captured.out
    assert "INFO | Nenhum JSON foi salvo automaticamente." in captured.out


def test_harness_print_provider_request_reports_guard_block(monkeypatch, capsys) -> None:
    monkeypatch.setattr(harness, "get_settings", lambda: make_shopee_settings(enabled=False))

    exit_code = harness.run(
        [
            "--marketplace",
            "shopee",
            "--niche",
            "maquiagem",
            "--print-provider-request",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | HTTP real bloqueado por configuração insegura" in captured.err
    assert "real HTTP flag enabled" in captured.err


def test_harness_print_provider_request_blocks_non_shopee(capsys) -> None:
    exit_code = harness.run(
        [
            "--marketplace",
            "amazon",
            "--niche",
            "maquiagem",
            "--print-provider-request",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Preview de request disponível apenas para Shopee" in captured.err
    assert "AÇÃO | Use --marketplace shopee." in captured.err

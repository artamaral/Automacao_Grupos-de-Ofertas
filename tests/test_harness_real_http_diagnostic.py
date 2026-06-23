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


def test_harness_real_http_diagnostic_succeeds_without_external_call(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(harness, "get_settings", make_shopee_settings)
    monkeypatch.setenv("SHOPEE_BASE_URL", "https://api.shopee.test")

    exit_code = harness.run(
        [
            "--marketplace",
            "shopee",
            "--niche",
            "maquiagem",
            "--diagnose-real-http",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "INFO | Diagnóstico de HTTP real aprovado" in captured.out
    assert "INFO | Nenhuma chamada HTTP foi executada." in captured.out
    assert "INFO | Nenhuma publicação foi executada." in captured.out
    assert "INFO | Nenhum JSON foi salvo automaticamente." in captured.out
    assert "INFO | Encontradas" not in captured.out


def test_harness_real_http_diagnostic_reports_guard_block(monkeypatch, capsys) -> None:
    monkeypatch.setattr(harness, "get_settings", lambda: make_shopee_settings(enabled=False))

    exit_code = harness.run(
        [
            "--marketplace",
            "shopee",
            "--niche",
            "maquiagem",
            "--diagnose-real-http",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | HTTP real bloqueado por configuração insegura" in captured.err
    assert "real HTTP flag enabled" in captured.err


def test_harness_real_http_diagnostic_skips_mock(capsys) -> None:
    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--diagnose-real-http",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "WARN | Diagnóstico de HTTP real não se aplica" in captured.out
    assert "AÇÃO | Use --marketplace shopee ou --marketplace amazon." in captured.out

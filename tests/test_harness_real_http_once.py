from ofertas_bot import harness
from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.settings import Settings


def make_shopee_settings(enabled: bool = True) -> Settings:
    values = {
        "enable_real_http": enabled,
        "shopee_partner_id": "partner",
        "shopee_tracking_id": "tracking",
    }
    values["shopee_" + "secret_key"] = "credential"
    return Settings(**values)


def sample_offer() -> Offer:
    return Offer(
        marketplace=Marketplace.SHOPEE,
        title="Oferta real controlada",
        url="https://example.test/oferta",
        image_url="https://example.test/oferta.jpg",
        price=49.9,
        old_price=89.9,
        commission_rate=0.08,
        sales_count=120,
        rating=4.8,
        niche="maquiagem",
        is_prime_or_free_shipping=True,
    )


def test_harness_execute_real_http_once_collects_without_publish_or_save(
    monkeypatch,
    capsys,
) -> None:
    calls = []

    def fake_collect(self, marketplace: Marketplace, niche: str, limit: int):
        calls.append((marketplace, niche, limit))
        return [sample_offer()]

    monkeypatch.setattr(harness, "get_settings", make_shopee_settings)
    monkeypatch.setenv("SHOPEE_BASE_URL", "https://api.shopee.test")
    monkeypatch.setattr(harness.CollectorAgent, "collect", fake_collect)

    exit_code = harness.run(
        [
            "--marketplace",
            "shopee",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--execute-real-http-once",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert calls == [(Marketplace.SHOPEE, "maquiagem", 1)]
    assert "INFO | Chamada HTTP real controlada concluída" in captured.out
    assert "INFO | Ofertas normalizadas recebidas: 1" in captured.out
    assert "INFO | Nenhuma publicação foi executada." in captured.out
    assert "INFO | Nenhum JSON foi salvo automaticamente." in captured.out
    assert "Oferta #1" not in captured.out
    assert "Ofertas normalizadas salvas" not in captured.out


def test_harness_execute_real_http_once_blocks_mock(capsys) -> None:
    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--execute-real-http-once",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Chamada HTTP real não se aplica ao marketplace mock" in captured.err
    assert "AÇÃO | Use --marketplace shopee ou --marketplace amazon." in captured.err


def test_harness_execute_real_http_once_reports_guard_block(monkeypatch, capsys) -> None:
    monkeypatch.setattr(harness, "get_settings", lambda: make_shopee_settings(enabled=False))

    exit_code = harness.run(
        [
            "--marketplace",
            "shopee",
            "--niche",
            "maquiagem",
            "--execute-real-http-once",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | HTTP real bloqueado por configuração insegura" in captured.err
    assert "real HTTP flag enabled" in captured.err


def test_harness_real_http_modes_are_mutually_exclusive(capsys) -> None:
    exit_code = harness.run(
        [
            "--marketplace",
            "shopee",
            "--niche",
            "maquiagem",
            "--diagnose-real-http",
            "--execute-real-http-once",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Modo de HTTP real inválido" in captured.err
    assert "--diagnose-real-http ou --execute-real-http-once" in captured.err

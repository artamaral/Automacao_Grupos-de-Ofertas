from ofertas_bot import harness
from ofertas_bot.models import Marketplace
from ofertas_bot.providers.real_http_guard import RealHttpValidationError


def test_harness_handles_real_http_guard_error(monkeypatch, capsys) -> None:
    def raise_guard_error(self, marketplace: Marketplace, niche: str, limit: int):
        raise RealHttpValidationError("Real HTTP for Shopee is blocked")

    monkeypatch.setattr(harness.CollectorAgent, "collect", raise_guard_error)

    exit_code = harness.run(["--marketplace", "mock", "--niche", "maquiagem", "--limit", "1"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | HTTP real bloqueado por configuração insegura" in captured.err
    assert "DETALHE | Real HTTP for Shopee is blocked" in captured.err
    assert "AÇÃO | Revise o checklist de produção" in captured.err

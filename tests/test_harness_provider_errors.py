from ofertas_bot import harness
from ofertas_bot.models import Marketplace
from ofertas_bot.providers.http import ProviderHttpError
from ofertas_bot.providers.shopee_gateway import ShopeePayloadError


def test_harness_handles_shopee_payload_error(monkeypatch, capsys) -> None:
    def raise_payload_error(self, marketplace: Marketplace, niche: str, limit: int):
        raise ShopeePayloadError("Shopee response field 'items' must be a list")

    monkeypatch.setattr(harness.CollectorAgent, "collect", raise_payload_error)

    exit_code = harness.run(["--marketplace", "shopee", "--niche", "maquiagem"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Resposta da Shopee em formato inesperado" in captured.err
    assert "DETALHE | Shopee response field 'items' must be a list" in captured.err
    assert "AÇÃO | Valide o payload retornado pelo provider" in captured.err


def test_harness_handles_provider_http_error(monkeypatch, capsys) -> None:
    def raise_http_error(self, marketplace: Marketplace, niche: str, limit: int):
        raise ProviderHttpError("Shopee request failed with status=500")

    monkeypatch.setattr(harness.CollectorAgent, "collect", raise_http_error)

    exit_code = harness.run(["--marketplace", "shopee", "--niche", "maquiagem"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Falha na resposta HTTP da Shopee" in captured.err
    assert "DETALHE | Shopee request failed with status=500" in captured.err
    assert "AÇÃO | Verifique status, rate limit" in captured.err

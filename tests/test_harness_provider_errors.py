from ofertas_bot import harness
from ofertas_bot.models import Marketplace
from ofertas_bot.providers.amazon_gateway import AmazonPayloadError
from ofertas_bot.providers.http import ProviderHttpError
from ofertas_bot.providers.shopee_gateway import ShopeePayloadError
from ofertas_bot.providers.transport import HttpTransportError


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


def test_harness_handles_amazon_payload_error(monkeypatch, capsys) -> None:
    def raise_payload_error(self, marketplace: Marketplace, niche: str, limit: int):
        raise AmazonPayloadError("Amazon response field 'SearchResult.Items' must be a list")

    monkeypatch.setattr(harness.CollectorAgent, "collect", raise_payload_error)

    exit_code = harness.run(["--marketplace", "amazon", "--niche", "casa"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Resposta da Amazon em formato inesperado" in captured.err
    assert "DETALHE | Amazon response field 'SearchResult.Items' must be a list" in captured.err
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


def test_harness_handles_transport_error(monkeypatch, capsys) -> None:
    def raise_transport_error(self, marketplace: Marketplace, niche: str, limit: int):
        raise HttpTransportError("HTTP transport request failed")

    monkeypatch.setattr(harness.CollectorAgent, "collect", raise_transport_error)

    exit_code = harness.run(["--marketplace", "amazon", "--niche", "casa"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Falha de transporte HTTP da Amazon" in captured.err
    assert "DETALHE | HTTP transport request failed" in captured.err
    assert "AÇÃO | Verifique conexão, timeout e configuração" in captured.err

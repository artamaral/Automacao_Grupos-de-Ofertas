from ofertas_bot import harness
from ofertas_bot.models import Marketplace
from ofertas_bot.providers.gateway import ProviderLimitError


def test_harness_rejects_zero_limit(capsys) -> None:
    exit_code = harness.run(["--marketplace", "mock", "--niche", "maquiagem", "--limit", "0"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Limite de ofertas inválido" in captured.err
    assert "DETALHE | --limit deve ser maior que zero. Valor recebido: 0" in captured.err
    assert "AÇÃO | Informe um valor positivo" in captured.err


def test_harness_rejects_negative_limit(capsys) -> None:
    exit_code = harness.run(["--marketplace", "mock", "--niche", "maquiagem", "--limit", "-1"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Limite de ofertas inválido" in captured.err
    assert "DETALHE | --limit deve ser maior que zero. Valor recebido: -1" in captured.err
    assert "AÇÃO | Informe um valor positivo" in captured.err


def test_harness_handles_provider_limit_error(monkeypatch, capsys) -> None:
    def raise_limit_error(self, marketplace: Marketplace, niche: str, limit: int):
        raise ProviderLimitError("Provider limit must be greater than zero. Received: 0")

    monkeypatch.setattr(harness.CollectorAgent, "collect", raise_limit_error)

    exit_code = harness.run(["--marketplace", "mock", "--niche", "maquiagem", "--limit", "1"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Limite interno de provider inválido" in captured.err
    assert "DETALHE | Provider limit must be greater than zero. Received: 0" in captured.err
    assert "AÇÃO | Revise a origem do limite" in captured.err

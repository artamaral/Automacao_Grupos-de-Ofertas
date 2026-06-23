from ofertas_bot import harness


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

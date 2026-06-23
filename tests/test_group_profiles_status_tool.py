from ofertas_bot.tools import group_profiles_status


def test_group_profiles_status_lists_active_profiles(capsys) -> None:
    exit_code = group_profiles_status.run([])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "INFO | Perfis ativos cadastrados" in captured.out
    assert "INFO | group=maquiagem-vip" in captured.out
    assert "INFO | group=casa-achadinhos" in captured.out
    assert "INFO | Nenhuma chamada externa foi executada." in captured.out
    assert "INFO | Nenhuma publicação foi executada." in captured.out


def test_group_profiles_status_filters_by_niche(capsys) -> None:
    exit_code = group_profiles_status.run(["--niche", "maquiagem"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "INFO | niche=maquiagem" in captured.out
    assert "INFO | group=maquiagem-vip" in captured.out
    assert "INFO | group=casa-achadinhos" not in captured.out


def test_group_profiles_status_handles_empty_filter(capsys) -> None:
    exit_code = group_profiles_status.run(["--niche", "nao-existe"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "INFO | Nenhum perfil encontrado" in captured.out
    assert "INFO | Nenhuma chamada externa foi executada." in captured.out

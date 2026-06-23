from ofertas_bot import harness


def test_harness_warns_when_save_json_uses_current_directory(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--save-json",
            "ofertas.json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "WARN | O arquivo ofertas.json será salvo no diretório atual" in captured.out
    assert (tmp_path / "ofertas.json").exists()


def test_harness_does_not_warn_when_save_json_uses_subdirectory(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = harness.run(
        [
            "--marketplace",
            "mock",
            "--niche",
            "maquiagem",
            "--limit",
            "1",
            "--save-json",
            "tmp/ofertas.json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Prefira .data/, tmp/ ou exports/" not in captured.out
    assert (tmp_path / "tmp" / "ofertas.json").exists()

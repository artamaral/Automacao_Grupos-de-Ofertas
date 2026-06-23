from ofertas_bot.settings import Settings


def test_settings_keep_real_http_disabled_by_default() -> None:
    settings = Settings()

    assert settings.enable_real_http is False


def test_settings_ignore_dotenv_during_pytest_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_settings.py::test")
    tmp_path.joinpath(".env").write_text("ENABLE_REAL_HTTP=true\n", encoding="utf-8")

    settings = Settings()

    assert settings.enable_real_http is False


def test_settings_can_opt_into_env_file_when_needed(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_settings.py::test")
    env_file = tmp_path / ".env"
    env_file.write_text("ENABLE_REAL_HTTP=true\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.enable_real_http is True

from ofertas_bot.settings import Settings


def test_settings_keep_real_http_disabled_by_default() -> None:
    settings = Settings()

    assert settings.enable_real_http is False

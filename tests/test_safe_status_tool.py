from ofertas_bot.settings import Settings
from ofertas_bot.tools import safe_status


def make_shopee_settings(
    *,
    enable_real_http: bool = True,
    enable_real_publish: bool = False,
) -> Settings:
    values = {
        "enable_real_http": enable_real_http,
        "enable_real_publish": enable_real_publish,
        "shopee_partner_id": "partner",
        "shopee_tracking_id": "tracking",
    }
    values["shopee_" + "secret_key"] = "credential"
    return Settings(**values)


def test_safe_status_allows_confirmed_shopee_environment(monkeypatch, capsys) -> None:
    monkeypatch.setattr(safe_status, "get_settings", make_shopee_settings)
    monkeypatch.setenv("SHOPEE_BASE_URL", "https://api.shopee.test")
    monkeypatch.setenv("SHOPEE_SEARCH_PATH_CONFIRMED", "true")

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "INFO | Ambiente pronto para chamada real controlada" in captured.out
    assert "INFO | search_path_confirmed=true" in captured.out


def test_safe_status_does_not_print_sensitive_configuration(monkeypatch, capsys) -> None:
    monkeypatch.setattr(safe_status, "get_settings", make_shopee_settings)
    monkeypatch.setenv("SHOPEE_BASE_URL", "https://api.shopee.test")
    monkeypatch.setenv("SHOPEE_SEARCH_PATH_CONFIRMED", "true")

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    combined_output = captured.out + captured.err
    assert exit_code == 0
    assert "partner" not in combined_output
    assert "tracking" not in combined_output
    assert "credential" not in combined_output


def test_safe_status_blocks_unconfirmed_shopee_path(monkeypatch, capsys) -> None:
    monkeypatch.setattr(safe_status, "get_settings", make_shopee_settings)
    monkeypatch.setenv("SHOPEE_BASE_URL", "https://api.shopee.test")
    monkeypatch.delenv("SHOPEE_SEARCH_PATH_CONFIRMED", raising=False)

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Ambiente bloqueado para chamada real" in captured.err
    assert "DETALHE | endpoint da Shopee não confirmado" in captured.err


def test_safe_status_blocks_disabled_real_http(monkeypatch, capsys) -> None:
    def get_settings_stub() -> Settings:
        return make_shopee_settings(enable_real_http=False)

    monkeypatch.setattr(safe_status, "get_settings", get_settings_stub)
    monkeypatch.setenv("SHOPEE_BASE_URL", "https://api.shopee.test")
    monkeypatch.setenv("SHOPEE_SEARCH_PATH_CONFIRMED", "true")

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "real HTTP flag enabled" in captured.err


def test_safe_status_blocks_real_publish(monkeypatch, capsys) -> None:
    def get_settings_stub() -> Settings:
        return make_shopee_settings(enable_real_publish=True)

    monkeypatch.setattr(safe_status, "get_settings", get_settings_stub)
    monkeypatch.setenv("SHOPEE_BASE_URL", "https://api.shopee.test")
    monkeypatch.setenv("SHOPEE_SEARCH_PATH_CONFIRMED", "true")

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "DETALHE | publicação real habilitada" in captured.err

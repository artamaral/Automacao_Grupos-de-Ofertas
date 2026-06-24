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
        "shopee_partner_id": "123456789",
        "shopee_tracking_id": "tracking",
    }
    values["shopee_" + "secret_key"] = "credential"
    return Settings(**values)


def test_safe_status_allows_confirmed_shopee_environment(monkeypatch, capsys) -> None:
    monkeypatch.setattr(safe_status, "get_settings", make_shopee_settings)
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://api.shopee.test/graphql")

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "INFO | Ambiente pronto para chamada real controlada" in captured.out
    assert "INFO | graphql_url=https://api.shopee.test/graphql" in captured.out


def test_safe_status_does_not_print_sensitive_configuration(monkeypatch, capsys) -> None:
    monkeypatch.setattr(safe_status, "get_settings", make_shopee_settings)
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://api.shopee.test/graphql")

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    combined_output = captured.out + captured.err
    assert exit_code == 0
    assert "123456789" not in combined_output
    assert "tracking" not in combined_output
    assert "credential" not in combined_output


def test_safe_status_blocks_placeholder_shopee_graphql_url(monkeypatch, capsys) -> None:
    monkeypatch.setattr(safe_status, "get_settings", make_shopee_settings)
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://example.com")

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "ERRO | Ambiente bloqueado para chamada real" in captured.err
    assert "non-placeholder base URL" in captured.err


def test_safe_status_blocks_disabled_real_http(monkeypatch, capsys) -> None:
    def get_settings_stub() -> Settings:
        return make_shopee_settings(enable_real_http=False)

    monkeypatch.setattr(safe_status, "get_settings", get_settings_stub)
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://api.shopee.test/graphql")

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "real HTTP flag enabled" in captured.err


def test_safe_status_blocks_real_publish(monkeypatch, capsys) -> None:
    def get_settings_stub() -> Settings:
        return make_shopee_settings(enable_real_publish=True)

    monkeypatch.setattr(safe_status, "get_settings", get_settings_stub)
    monkeypatch.setenv("SHOPEE_GRAPHQL_URL", "https://api.shopee.test/graphql")

    exit_code = safe_status.run(["--marketplace", "shopee"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "DETALHE | publicacao real habilitada" in captured.err

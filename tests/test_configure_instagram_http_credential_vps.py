from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts/n8n/configure_instagram_http_credential_vps.py"
)
SPEC = importlib.util.spec_from_file_location("configure_instagram_http_credential_vps", MODULE_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_parse_args_supports_inspect_mode() -> None:
    args = module.parse_args(["--inspect"])
    config = module.config_from_args(args)

    assert config.inspect is True
    assert config.apply is False


def test_validate_config_rejects_apply_and_inspect_together() -> None:
    args = module.parse_args(["--apply", "--inspect"])
    config = module.config_from_args(args)

    with pytest.raises(module.InstagramHttpCredentialError, match="nao podem ser usados juntos"):
        module.validate_config(config)


def test_remote_inspect_script_checks_env_usage_without_exposing_token() -> None:
    script = module.REMOTE_INSPECT_SCRIPT

    assert "export:credentials" in script
    assert '"value_uses_expression"' in script
    assert '"value_uses_env"' in script
    assert '"workflow_has_process_env"' in script
    assert '"workflow_has_env_expression"' in script
    assert "print(json.dumps(report, ensure_ascii=False))" in script
    assert "Bearer " in script


def test_remote_apply_script_falls_back_to_sql_delete_when_cli_is_missing() -> None:
    script = module.REMOTE_SCRIPT

    assert 'Command "delete:credentials" not found' in script
    assert "delete from credentials_entity where id =" in script
    assert "shared_credentials" in script
    assert "CREDENTIAL_SQL_REPLACED=" in script

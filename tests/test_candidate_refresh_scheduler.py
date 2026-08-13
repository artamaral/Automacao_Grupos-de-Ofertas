from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

WRAPPER_PATH = Path("scripts/ops/run_shopee_candidate_refresh.sh")
SERVICE_PATH = Path("deploy/systemd/shopee-candidate-refresh.service")
WATCHDOG_PATH = Path("scripts/ops/hermes_shopee_refresh_watchdog.py")

SPEC = importlib.util.spec_from_file_location("hermes_shopee_refresh_watchdog", WATCHDOG_PATH)
assert SPEC and SPEC.loader
watchdog = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = watchdog
SPEC.loader.exec_module(watchdog)


def test_wrapper_runs_refresh_optional_confirmation_and_planning_in_order() -> None:
    script = WRAPPER_PATH.read_text(encoding="utf-8")

    refresh_position = script.index("scripts/shopee/run_candidate_refresh.py")
    confirmation_position = script.index(
        "scripts/shopee/auto_confirm_candidate_unavailable.py"
    )
    planning_position = script.index("-m ofertas_bot.tools.plan_daily_dispatch")

    assert refresh_position < confirmation_position < planning_position
    assert 'if [[ "${AUTO_CONFIRM_UNAVAILABLE_ENABLED}" == "true" ]]; then' in script
    assert 'if [[ "${AUTO_CONFIRM_UNAVAILABLE_ENABLED}" != "true" ]]; then' not in script
    old_exec = 'exec "${PYTHON_BIN}" scripts/shopee/auto_confirm_candidate_unavailable.py'
    assert old_exec not in script


def test_wrapper_uses_fail_fast_and_applies_the_daily_plan() -> None:
    script = WRAPPER_PATH.read_text(encoding="utf-8")

    assert "set -Eeuo pipefail" in script
    command_start = script.index('"${PYTHON_BIN}" -m ofertas_bot.tools.plan_daily_dispatch')
    planning_command = script[command_start:]
    assert '--profile "${PROFILE}"' in planning_command
    assert '--marketplace "${MARKETPLACE}"' in planning_command
    assert "--apply" in planning_command


def test_service_describes_the_combined_chain() -> None:
    service = SERVICE_PATH.read_text(encoding="utf-8")

    assert "Description=Shopee candidate refresh and daily dispatch planning" in service
    assert "TimeoutStartSec=45min" in service


def test_watchdog_accepts_successful_combined_service() -> None:
    state = "Result=success\nExecMainStatus=0\nActiveState=inactive\nSubState=dead"

    assert watchdog.service_state_problems(state) == []


def test_watchdog_reports_planning_or_refresh_service_failure() -> None:
    state = "Result=exit-code\nExecMainStatus=1\nActiveState=failed\nSubState=failed"

    assert watchdog.service_state_problems(state) == [
        "service Result inesperado: exit-code",
        "service ExecMainStatus inesperado: 1",
    ]

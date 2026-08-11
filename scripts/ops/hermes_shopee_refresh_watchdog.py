#!/usr/bin/env python3
"""Hermes no_agent watchdog for the Shopee candidate refresh.

Read-only semantics:
- stdout empty: silent success
- stdout with text: Telegram alert
- exit != 0: watchdog error
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

VPS_HOST = "root@76.13.237.105"
SSH_KEY = "/opt/data/.ssh/hostinger_n8n_ed25519"
APP_DIR = PurePosixPath("/opt/automacao_grupo_compras/app")
SERVICE_NAME = "shopee-candidate-refresh.service"
TIMER_NAME = "shopee-candidate-refresh.timer"
PROFILE = "feminino"
LOOKBACK_AFTER_BRT = "07:00"


@dataclass(frozen=True)
class RemoteResult:
    returncode: int
    stdout: str
    stderr: str


def run_ssh(command: str, *, timeout: int = 45) -> RemoteResult:
    proc = subprocess.run(
        [
            "ssh",
            "-i",
            SSH_KEY,
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "LogLevel=ERROR",
            VPS_HOST,
            command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return RemoteResult(
        returncode=proc.returncode,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )


def load_remote_report() -> tuple[dict[str, Any], str]:
    command = (
        "python3 - <<'PY'\n"
        "import json\n"
        "from datetime import datetime\n"
        "from pathlib import Path\n"
        f"base = Path('{APP_DIR}/.data/candidate_refresh/{PROFILE}')\n"
        "today = datetime.now().date()\n"
        "reports = []\n"
        "if base.exists():\n"
        "    for path in base.glob('*/run_report.json'):\n"
        "        stat = path.stat()\n"
        "        dt = datetime.fromtimestamp(stat.st_mtime)\n"
        f"        if dt.date() == today and dt.strftime('%H:%M') >= '{LOOKBACK_AFTER_BRT}':\n"
        "            reports.append((stat.st_mtime, path))\n"
        "if not reports:\n"
        "    print(json.dumps({'error': 'NO_REPORT_TODAY'}))\n"
        "else:\n"
        "    path = sorted(reports)[-1][1]\n"
        "    print(json.dumps({'path': str(path), 'report': json.loads(path.read_text())}))\n"
        "PY"
    )
    result = run_ssh(command)
    if result.returncode != 0:
        raise RuntimeError(f"SSH report check failed: {result.stderr or result.stdout}")
    data = json.loads(result.stdout)
    if data.get("error") == "NO_REPORT_TODAY":
        raise FileNotFoundError("nenhum run_report.json de hoje apos 07:00 BRT")
    return data["report"], data["path"]


def check_systemd() -> tuple[str, str, str]:
    command = (
        f"systemctl is-enabled {TIMER_NAME}; "
        f"systemctl is-active {TIMER_NAME}; "
        f"systemctl show {SERVICE_NAME} "
        "--property=Result,ExecMainStatus,ActiveState,SubState,InactiveExitTimestamp "
        "--no-pager"
    )
    result = run_ssh(command)
    if result.returncode not in {0, 1, 3}:
        raise RuntimeError(f"systemd check failed: {result.stderr or result.stdout}")
    lines = result.stdout.splitlines()
    timer_enabled = lines[0] if len(lines) >= 1 else "unknown"
    timer_active = lines[1] if len(lines) >= 2 else "unknown"
    service_state = "\n".join(lines[2:]) if len(lines) > 2 else "unknown"
    return timer_enabled, timer_active, service_state


def report_value(report: dict[str, Any], *path: str) -> Any:
    current: Any = report
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def build_alert(
    *,
    problems: list[str],
    timer_enabled: str,
    timer_active: str,
    service_state: str,
    report: dict[str, Any] | None,
    report_path: str | None,
) -> str:
    lines = ["ALERTA refresh Shopee"]
    lines.extend(f"- {problem}" for problem in problems)
    lines.append(f"- timer: enabled={timer_enabled}, active={timer_active}")
    lines.append(f"- service: {service_state.replace(chr(10), '; ')}")
    if report:
        lines.append(f"- run_id: {report.get('run_id', '?')}")
        lines.append(f"- run_status: {report.get('run_status', '?')}")
        lines.append(f"- chamadas: {report_value(report, 'summary', 'api_calls_attempted')}")
        lines.append(f"- snapshots: {report_value(report, 'summary', 'snapshots_inserted')}")
        failures = (
            int(report_value(report, "summary", "failed_refreshes") or 0)
            + int(report_value(report, "summary", "no_node_refreshes") or 0)
        )
        lines.append(f"- falhas/no_node: {failures}")
        lines.append(f"- duracao_s: {report_value(report, 'summary', 'elapsed_seconds')}")
    if report_path:
        lines.append(f"- report: {report_path}")
    lines.append("- hipotese: refresh diario nao concluiu conforme contrato operacional")
    return "\n".join(lines)


def main() -> int:
    try:
        timer_enabled, timer_active, service_state = check_systemd()
        problems = []
        if timer_enabled != "enabled":
            problems.append(f"timer nao esta enabled: {timer_enabled}")
        if timer_active != "active":
            problems.append(f"timer nao esta active: {timer_active}")

        report = None
        report_path = None
        try:
            report, report_path = load_remote_report()
        except FileNotFoundError as error:
            problems.append(str(error))

        if report is not None:
            run_status = str(report.get("run_status", ""))
            attempts = int(report_value(report, "summary", "api_calls_attempted") or 0)
            snapshots = int(report_value(report, "summary", "snapshots_inserted") or 0)
            max_calls = int(report_value(report, "limits", "max_api_calls") or 0)
            elapsed = report_value(report, "summary", "elapsed_seconds")
            if not run_status.startswith(("completed", "partial")):
                problems.append(f"run_status inesperado: {run_status}")
            if attempts <= 0:
                problems.append("nenhuma chamada real registrada")
            if max_calls and attempts > max_calls:
                problems.append(f"chamadas acima do limite: {attempts}/{max_calls}")
            if attempts > 0 and snapshots <= 0:
                problems.append("nenhum snapshot inserido")
            if elapsed is None:
                problems.append("duration/elapsed_seconds ausente")

        if not problems:
            return 0
        print(
            build_alert(
                problems=problems,
                timer_enabled=timer_enabled,
                timer_active=timer_active,
                service_state=service_state,
                report=report,
                report_path=report_path,
            )
        )
        return 0
    except Exception as error:  # noqa: BLE001
        print(f"ERRO watchdog refresh Shopee: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

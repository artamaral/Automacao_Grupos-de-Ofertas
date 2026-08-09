from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ALLOWED_MODES = ("grupo-real", "teste-telefone", "dry-run")
SUMMARY_FIELDS = (
    "execution_id",
    "endpoint",
    "publish_id",
    "delivery_status",
    "adapter_response_type",
    "copy_template",
)
CHECK_ATTEMPTS = 12
CHECK_RETRY_SECONDS = 5
SENSITIVE_PATTERN = re.compile(
    r"(password|senha|cookie|token|api[-_ ]?key|x-api-key|authorization|secret)",
    re.IGNORECASE,
)


class OperationalRoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class RoundConfig:
    mode: str


@dataclass(frozen=True)
class StepResult:
    name: str
    stdout: str
    stderr: str
    returncode: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a complete guarded n8n operational round."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=ALLOWED_MODES,
        help="Operational mode. Required to avoid accidental real sends.",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> RoundConfig:
    return RoundConfig(mode=args.mode)


def sanitize_text(value: str) -> str:
    lines: list[str] = []
    for line in value.splitlines():
        if not SENSITIVE_PATTERN.search(line):
            lines.append(line)
            continue
        if "=" in line:
            key, _separator, _rest = line.partition("=")
            lines.append(f"{key}=<redacted>")
        elif ":" in line:
            key, _separator, _rest = line.partition(":")
            lines.append(f"{key}: <redacted>")
        else:
            lines.append("<redacted sensitive line>")
    return "\n".join(lines)


def print_step_output(result: StepResult) -> None:
    stdout = sanitize_text(result.stdout).strip()
    stderr = sanitize_text(result.stderr).strip()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)


def run_step(name: str, args: list[str]) -> StepResult:
    result = execute_step(name, args)
    print_step_output(result)
    if result.returncode != 0:
        raise OperationalRoundError(f"{name} falhou com codigo {result.returncode}")
    return result


def execute_step(name: str, args: list[str]) -> StepResult:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / name), *args],
        text=True,
        check=False,
        capture_output=True,
    )
    result = StepResult(
        name=name,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )
    return result


def info_fields(output: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in output.splitlines():
        if not line.startswith("INFO | "):
            continue
        body = line.removeprefix("INFO | ")
        key, separator, value = body.partition("=")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


def numeric_execution_id(output: str) -> str | None:
    execution_id = info_fields(output).get("execution_id")
    if execution_id and execution_id.isdigit():
        return execution_id
    return None


def check_args(mode: str, run_output: str) -> list[str]:
    args: list[str] = []
    execution_id = numeric_execution_id(run_output)
    if execution_id:
        args.extend(["--execution-id", execution_id])
    if mode in ("grupo-real", "teste-telefone"):
        args.append("--expect-real-image")
    return args


def print_final_summary(check_output: str) -> None:
    fields = info_fields(check_output)
    print("INFO | resumo_final=true")
    for field in SUMMARY_FIELDS:
        value = fields.get(field)
        if value not in (None, ""):
            print(f"INFO | {field}={value}")


def run_check_with_retry(args: list[str]) -> StepResult:
    last_result: StepResult | None = None
    for attempt in range(1, CHECK_ATTEMPTS + 1):
        result = execute_step("check_last_execution.py", args)
        if result.returncode == 0:
            print_step_output(result)
            return result
        last_result = result
        if attempt < CHECK_ATTEMPTS:
            print(
                "INFO | check_last_execution_retry="
                f"{attempt}/{CHECK_ATTEMPTS}; aguardando {CHECK_RETRY_SECONDS}s"
            )
            time.sleep(CHECK_RETRY_SECONDS)

    if last_result is not None:
        print_step_output(last_result)
    raise OperationalRoundError("check_last_execution.py falhou com codigo 1")


def run(config: RoundConfig) -> int:
    run_step("deploy_workflow_guard.py", ["--mode", config.mode])
    run_result = run_step("run_workflow_manual.py", ["--mode", config.mode])
    check_result = run_check_with_retry(check_args(config.mode, run_result.stdout))
    print_final_summary(check_result.stdout)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(config_from_args(parse_args(argv)))
    except OperationalRoundError as exc:
        print(f"ERRO | {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

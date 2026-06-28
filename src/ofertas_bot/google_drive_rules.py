from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOOGLE_DRIVE_RULES_DIR = PROJECT_ROOT / "n8n" / "google_sheets_seed"
RULES_DIR_ENV_VAR = "OFERTAS_RULES_DIR"


def resolve_rules_file(*, sheet_name: str, legacy_path: Path) -> Path:
    rules_dir = _configured_rules_dir()
    csv_path = rules_dir / f"{sheet_name}.csv"
    if csv_path.exists():
        return csv_path
    return legacy_path


def resolve_sheet_csv_path(path: Path, *, sheet_name: str) -> Path:
    if path.is_dir():
        return path / f"{sheet_name}.csv"
    return path


def _configured_rules_dir() -> Path:
    configured = os.getenv(RULES_DIR_ENV_VAR)
    if configured:
        return Path(configured)
    return DEFAULT_GOOGLE_DRIVE_RULES_DIR

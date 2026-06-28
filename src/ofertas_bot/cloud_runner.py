from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ofertas_bot import local_flow_cli

ALLOWED_PROFILES = ("feminino", "mae-e-bebe", "auto-e-moto")


class CloudRunnerError(ValueError):
    """Raised when the cloud runner request is invalid."""


@dataclass(frozen=True)
class CloudPathConfig:
    root_dir: Path
    app_dir: Path
    catalogs_dir: Path
    data_dir: Path


def resolve_path_config(
    *,
    root_dir: str = "",
    app_dir: str = "",
    catalogs_dir: str = "",
    data_dir: str = "",
) -> CloudPathConfig:
    resolved_root_dir = root_dir.strip() or os.getenv("N8N_OFERTAS_ROOT", "").strip()
    if not resolved_root_dir:
        msg = "N8N_OFERTAS_ROOT nao informado"
        raise CloudRunnerError(msg)

    resolved_app_dir = app_dir.strip() or os.getenv("N8N_OFERTAS_APP", "").strip()
    if not resolved_app_dir:
        resolved_app_dir = str(Path(resolved_root_dir) / "app" / "Automacao_Grupos-de-Ofertas")

    resolved_catalogs_dir = (
        catalogs_dir.strip() or os.getenv("N8N_OFERTAS_CATALOGS", "").strip()
    )
    if not resolved_catalogs_dir:
        resolved_catalogs_dir = str(Path(resolved_root_dir) / "catalogs")

    resolved_data_dir = data_dir.strip() or os.getenv("N8N_OFERTAS_DATA", "").strip()
    if not resolved_data_dir:
        resolved_data_dir = str(Path(resolved_root_dir) / "data")

    return CloudPathConfig(
        root_dir=Path(resolved_root_dir),
        app_dir=Path(resolved_app_dir),
        catalogs_dir=Path(resolved_catalogs_dir),
        data_dir=Path(resolved_data_dir),
    )


def parse_profiles(
    *,
    profile: str = "",
    profiles_csv: str = "",
    profiles: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    collected: list[str] = []
    if profile.strip():
        collected.append(profile.strip().lower())
    if profiles_csv.strip():
        collected.extend(
            item.strip().lower()
            for item in profiles_csv.split(",")
            if item.strip()
        )
    if profiles:
        collected.extend(item.strip().lower() for item in profiles if item.strip())
    if not collected:
        msg = "Nenhum profile informado"
        raise CloudRunnerError(msg)

    unique: list[str] = []
    for item in collected:
        if item not in ALLOWED_PROFILES:
            allowed = ", ".join(ALLOWED_PROFILES)
            msg = f"profile fora do contrato operacional: {item}. Permitidos: {allowed}"
            raise CloudRunnerError(msg)
        if item not in unique:
            unique.append(item)
    return tuple(unique)


def profile_catalog_path(path_config: CloudPathConfig, profile: str) -> Path:
    return path_config.catalogs_dir / profile / "clean_catalog_rating_4_8_plus.csv"


def profile_data_dir(path_config: CloudPathConfig, profile: str) -> Path:
    return path_config.data_dir / profile


def run_prepare_window(
    *,
    profile: str = "",
    profiles_csv: str = "",
    profiles: list[str] | tuple[str, ...] | None = None,
    root_dir: str = "",
    app_dir: str = "",
    catalogs_dir: str = "",
    data_dir: str = "",
    run_id: str = "",
) -> dict[str, Any]:
    path_config = resolve_path_config(
        root_dir=root_dir,
        app_dir=app_dir,
        catalogs_dir=catalogs_dir,
        data_dir=data_dir,
    )
    resolved_profiles = parse_profiles(
        profile=profile,
        profiles_csv=profiles_csv,
        profiles=profiles,
    )
    resolved_run_id = run_id.strip() or datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")

    results: list[dict[str, Any]] = []
    profiles_file = path_config.app_dir / "config" / "discovery_profiles.toml"
    for current_profile in resolved_profiles:
        catalog_path = profile_catalog_path(path_config, current_profile)
        if not catalog_path.exists() or catalog_path.stat().st_size <= 0:
            msg = f"Catalogo do profile nao encontrado ou vazio: {catalog_path}"
            raise CloudRunnerError(msg)

        current_data_dir = profile_data_dir(path_config, current_profile)
        current_data_dir.mkdir(parents=True, exist_ok=True)
        exit_code = _run_local_flow(
            app_dir=path_config.app_dir,
            argv=[
                "--stage",
                "prepare",
                "--profile",
                current_profile,
                "--profiles-file",
                str(profiles_file),
                "--data-dir",
                str(current_data_dir),
                "--catalog-file",
                str(catalog_path),
            ],
        )
        if exit_code != 0:
            msg = f"Prepare da janela falhou para profile={current_profile} com exit code {exit_code}"
            raise CloudRunnerError(msg)
        results.append(
            {
                "profile": current_profile,
                "status": "ok",
                "catalog_path": str(catalog_path),
                "data_dir": str(current_data_dir),
            }
        )

    summary = {
        "stage": "prepare",
        "run_id": resolved_run_id,
        "profiles": results,
        "total_profiles": len(results),
    }
    summary_path = path_config.data_dir / f"window_prepare_summary_{resolved_run_id}.json"
    save_json_file(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    return summary


def run_finalize_window(
    *,
    profile: str = "",
    profiles_csv: str = "",
    profiles: list[str] | tuple[str, ...] | None = None,
    root_dir: str = "",
    app_dir: str = "",
    catalogs_dir: str = "",
    data_dir: str = "",
    run_id: str = "",
) -> dict[str, Any]:
    path_config = resolve_path_config(
        root_dir=root_dir,
        app_dir=app_dir,
        catalogs_dir=catalogs_dir,
        data_dir=data_dir,
    )
    resolved_profiles = parse_profiles(
        profile=profile,
        profiles_csv=profiles_csv,
        profiles=profiles,
    )
    resolved_run_id = run_id.strip() or datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")

    results: list[dict[str, Any]] = []
    for current_profile in resolved_profiles:
        current_data_dir = profile_data_dir(path_config, current_profile)
        exit_code = _run_local_flow(
            app_dir=path_config.app_dir,
            argv=[
                "--stage",
                "finalize",
                "--data-dir",
                str(current_data_dir),
            ],
        )
        if exit_code != 0:
            msg = f"Finalize da janela falhou para profile={current_profile} com exit code {exit_code}"
            raise CloudRunnerError(msg)
        results.append(
            {
                "profile": current_profile,
                "status": "ok",
                "data_dir": str(current_data_dir),
                "dispatch_artifact": str(current_data_dir / "dispatch_artifact.json"),
                "dispatch_report": str(current_data_dir / "dispatch_report.json"),
            }
        )

    summary = {
        "stage": "finalize",
        "run_id": resolved_run_id,
        "profiles": results,
        "total_profiles": len(results),
    }
    summary_path = path_config.data_dir / f"window_finalize_summary_{resolved_run_id}.json"
    save_json_file(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    return summary


def save_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def health_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "ofertas-cloud-runner",
        "allowed_profiles": list(ALLOWED_PROFILES),
    }


def _run_local_flow(*, app_dir: Path, argv: list[str]) -> int:
    with _pushd(app_dir):
        return local_flow_cli.run(argv)


@contextmanager
def _pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ofertas_bot import local_flow_cli
from ofertas_bot.storage.json_message_draft_store import message_draft_from_json
from ofertas_bot.storage.json_selection_state_store import (
    JsonSelectionStateStore,
    update_selection_state_last_sent_at,
)

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


def parse_allowed_targets(
    *,
    allowed_targets_csv: str = "",
    allowed_targets: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    collected: list[str] = []
    if allowed_targets_csv.strip():
        collected.extend(
            item.strip()
            for item in allowed_targets_csv.split(",")
            if item.strip()
        )
    if allowed_targets:
        collected.extend(item.strip() for item in allowed_targets if item.strip())

    unique: list[str] = []
    for item in collected:
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
    profiles_file = path_config.app_dir / "n8n" / "google_sheets_seed" / "discovery_profiles.csv"
    if not profiles_file.exists():
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
            msg = (
                "Prepare da janela falhou para "
                f"profile={current_profile} com exit code {exit_code}"
            )
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
    defer_last_sent_at: bool = True,
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
                *(
                    ["--defer-last-sent-at"]
                    if defer_last_sent_at
                    else []
                ),
            ],
        )
        if exit_code != 0:
            msg = (
                "Finalize da janela falhou para "
                f"profile={current_profile} com exit code {exit_code}"
            )
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


def load_dispatch_window(
    *,
    profile: str = "",
    profiles_csv: str = "",
    profiles: list[str] | tuple[str, ...] | None = None,
    root_dir: str = "",
    app_dir: str = "",
    catalogs_dir: str = "",
    data_dir: str = "",
    run_id: str = "",
    allowed_targets_csv: str = "",
    allowed_targets: list[str] | tuple[str, ...] | None = None,
    include_blocked: bool = False,
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
    resolved_allowed_targets = parse_allowed_targets(
        allowed_targets_csv=allowed_targets_csv,
        allowed_targets=allowed_targets,
    )

    profile_rows: list[dict[str, Any]] = []
    deliveries: list[dict[str, Any]] = []

    for current_profile in resolved_profiles:
        current_data_dir = profile_data_dir(path_config, current_profile)
        artifact_path = current_data_dir / "dispatch_artifact.json"
        artifact = _load_json_object(artifact_path)
        raw_targets = artifact.get("targets", [])
        if not isinstance(raw_targets, list):
            msg = f"dispatch artifact invalido para profile={current_profile}"
            raise CloudRunnerError(msg)

        selected_targets: list[dict[str, Any]] = []
        profile_delivery_count = 0
        for raw_target in raw_targets:
            if not isinstance(raw_target, dict):
                continue
            target_name = str(raw_target.get("target", "")).strip()
            if not target_name:
                continue
            if resolved_allowed_targets and target_name not in resolved_allowed_targets:
                continue

            status = str(raw_target.get("status", "ready")).strip().lower()
            quiet_period_active = bool(raw_target.get("quiet_period_active", False))
            if not include_blocked and (status == "blocked" or quiet_period_active):
                continue

            raw_messages = raw_target.get("messages", [])
            if not isinstance(raw_messages, list):
                continue

            selected_targets.append(
                {
                    "target": target_name,
                    "adapter_kind": str(raw_target.get("adapter_kind", "")).strip().lower(),
                    "status": status,
                    "available_message_count": int(
                        raw_target.get("available_message_count", len(raw_messages))
                    ),
                    "selected_message_count": int(
                        raw_target.get("selected_message_count", len(raw_messages))
                    ),
                    "skipped_message_count": int(raw_target.get("skipped_message_count", 0)),
                    "blocked_reason": raw_target.get("blocked_reason"),
                    "selection_reason": raw_target.get("selection_reason"),
                    "min_interval_seconds": int(raw_target.get("min_interval_seconds", 0)),
                    "first_planned_at": raw_target.get("first_planned_at"),
                    "last_planned_at": raw_target.get("last_planned_at"),
                    "message_count": len(raw_messages),
                }
            )

            for raw_message in raw_messages:
                if not isinstance(raw_message, dict):
                    continue
                manifest_item_number = int(raw_message.get("manifest_item_number", 0))
                if manifest_item_number <= 0:
                    continue
                profile_delivery_count += 1
                deliveries.append(
                    {
                        "delivery_id": (
                            f"{current_profile}:{target_name}:{manifest_item_number}"
                        ),
                        "profile": current_profile,
                        "target": target_name,
                        "adapter_kind": str(raw_target.get("adapter_kind", "")).strip().lower(),
                        "manifest_item_number": manifest_item_number,
                        "created_at": str(raw_message.get("created_at", "")),
                        "planned_at": str(raw_message.get("planned_at", "")),
                        "planned_offset_seconds": int(
                            raw_message.get("planned_offset_seconds", 0)
                        ),
                        "status": str(raw_message.get("status", "")),
                        "text": str(raw_message.get("text", "")),
                        "offer": raw_message.get("offer"),
                        "draft": raw_message.get("draft"),
                    }
                )

        profile_rows.append(
            {
                "profile": current_profile,
                "data_dir": str(current_data_dir),
                "dispatch_artifact": str(artifact_path),
                "target_count": len(selected_targets),
                "delivery_count": profile_delivery_count,
                "targets": selected_targets,
            }
        )

    return {
        "stage": "dispatch-window",
        "run_id": resolved_run_id,
        "allowed_targets": list(resolved_allowed_targets),
        "include_blocked": include_blocked,
        "profiles": profile_rows,
        "total_profiles": len(profile_rows),
        "total_targets": sum(row["target_count"] for row in profile_rows),
        "total_deliveries": len(deliveries),
        "deliveries": deliveries,
    }


def run_window(
    *,
    profile: str = "",
    profiles_csv: str = "",
    profiles: list[str] | tuple[str, ...] | None = None,
    root_dir: str = "",
    app_dir: str = "",
    catalogs_dir: str = "",
    data_dir: str = "",
    run_id: str = "",
    allowed_targets_csv: str = "",
    allowed_targets: list[str] | tuple[str, ...] | None = None,
    include_blocked: bool = False,
) -> dict[str, Any]:
    resolved_run_id = run_id.strip() or datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    prepare = run_prepare_window(
        profile=profile,
        profiles_csv=profiles_csv,
        profiles=profiles,
        root_dir=root_dir,
        app_dir=app_dir,
        catalogs_dir=catalogs_dir,
        data_dir=data_dir,
        run_id=resolved_run_id,
    )
    finalize = run_finalize_window(
        profile=profile,
        profiles_csv=profiles_csv,
        profiles=profiles,
        root_dir=root_dir,
        app_dir=app_dir,
        catalogs_dir=catalogs_dir,
        data_dir=data_dir,
        run_id=resolved_run_id,
        defer_last_sent_at=True,
    )
    dispatch = load_dispatch_window(
        profile=profile,
        profiles_csv=profiles_csv,
        profiles=profiles,
        root_dir=root_dir,
        app_dir=app_dir,
        catalogs_dir=catalogs_dir,
        data_dir=data_dir,
        run_id=resolved_run_id,
        allowed_targets_csv=allowed_targets_csv,
        allowed_targets=allowed_targets,
        include_blocked=include_blocked,
    )
    return {
        "stage": "run-window",
        "run_id": resolved_run_id,
        "prepare_summary_path": prepare.get("summary_path"),
        "finalize_summary_path": finalize.get("summary_path"),
        "allowed_targets": dispatch["allowed_targets"],
        "include_blocked": include_blocked,
        "profiles": dispatch["profiles"],
        "total_profiles": dispatch["total_profiles"],
        "total_targets": dispatch["total_targets"],
        "total_deliveries": dispatch["total_deliveries"],
        "deliveries": dispatch["deliveries"],
    }


def confirm_delivery(
    *,
    profile: str,
    target: str,
    manifest_item_number: int,
    root_dir: str = "",
    app_dir: str = "",
    catalogs_dir: str = "",
    data_dir: str = "",
    sent_at: str = "",
) -> dict[str, Any]:
    return confirm_window_deliveries(
        deliveries=[
            {
                "profile": profile,
                "target": target,
                "manifest_item_number": manifest_item_number,
            }
        ],
        root_dir=root_dir,
        app_dir=app_dir,
        catalogs_dir=catalogs_dir,
        data_dir=data_dir,
        sent_at=sent_at,
    )


def confirm_window_deliveries(
    *,
    deliveries: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    root_dir: str = "",
    app_dir: str = "",
    catalogs_dir: str = "",
    data_dir: str = "",
    sent_at: str = "",
) -> dict[str, Any]:
    if not deliveries:
        msg = "Nenhuma entrega confirmada informada"
        raise CloudRunnerError(msg)

    path_config = resolve_path_config(
        root_dir=root_dir,
        app_dir=app_dir,
        catalogs_dir=catalogs_dir,
        data_dir=data_dir,
    )
    resolved_sent_at = sent_at.strip() or datetime.now(UTC).replace(microsecond=0).isoformat()

    grouped_by_profile: dict[str, list[tuple[str, int]]] = {}
    for item in deliveries:
        if not isinstance(item, dict):
            msg = "Entrega confirmada deve ser um objeto"
            raise CloudRunnerError(msg)
        current_profile = str(item.get("profile", "")).strip().lower()
        current_target = str(item.get("target", "")).strip()
        manifest_item_number = int(item.get("manifest_item_number", 0))
        if current_profile not in ALLOWED_PROFILES:
            msg = f"profile fora do contrato operacional: {current_profile}"
            raise CloudRunnerError(msg)
        if not current_target:
            msg = "Entrega confirmada sem target"
            raise CloudRunnerError(msg)
        if manifest_item_number <= 0:
            msg = "Entrega confirmada sem manifest_item_number valido"
            raise CloudRunnerError(msg)
        grouped_by_profile.setdefault(current_profile, []).append(
            (current_target, manifest_item_number)
        )

    confirmed_rows: list[dict[str, Any]] = []
    for current_profile, requested_items in grouped_by_profile.items():
        current_data_dir = profile_data_dir(path_config, current_profile)
        selection_state_path = current_data_dir / "selection_state.json"
        artifact_path = current_data_dir / "dispatch_artifact.json"
        drafts = _load_confirmed_drafts(
            artifact_path=artifact_path,
            requested_items=requested_items,
        )
        store = JsonSelectionStateStore(path=selection_state_path)
        records = store.load()
        updated = update_selection_state_last_sent_at(
            records,
            drafts=drafts,
            last_sent_at=resolved_sent_at,
        )
        store.save(updated)
        confirmed_rows.extend(
            {
                "profile": current_profile,
                "target": target_name,
                "manifest_item_number": manifest_item_number,
            }
            for target_name, manifest_item_number in requested_items
        )

    return {
        "stage": "confirm-window-deliveries",
        "sent_at": resolved_sent_at,
        "profiles_updated": sorted(grouped_by_profile),
        "confirmed_count": len(confirmed_rows),
        "confirmed_deliveries": confirmed_rows,
    }


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


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        msg = f"Nao foi possivel ler {path}"
        raise CloudRunnerError(msg) from error
    except json.JSONDecodeError as error:
        msg = f"JSON invalido em {path}"
        raise CloudRunnerError(msg) from error

    if not isinstance(payload, dict):
        msg = f"Arquivo deve conter objeto JSON: {path}"
        raise CloudRunnerError(msg)
    return payload


def _load_confirmed_drafts(
    *,
    artifact_path: Path,
    requested_items: list[tuple[str, int]],
) -> tuple[Any, ...]:
    artifact = _load_json_object(artifact_path)
    raw_targets = artifact.get("targets", [])
    if not isinstance(raw_targets, list):
        msg = f"dispatch artifact invalido: {artifact_path}"
        raise CloudRunnerError(msg)

    requested_set = set(requested_items)
    found: dict[tuple[str, int], Any] = {}
    for raw_target in raw_targets:
        if not isinstance(raw_target, dict):
            continue
        target_name = str(raw_target.get("target", "")).strip()
        raw_messages = raw_target.get("messages", [])
        if not target_name or not isinstance(raw_messages, list):
            continue
        for raw_message in raw_messages:
            if not isinstance(raw_message, dict):
                continue
            manifest_item_number = int(raw_message.get("manifest_item_number", 0))
            key = (target_name, manifest_item_number)
            if key not in requested_set:
                continue
            found[key] = message_draft_from_json(raw_message.get("draft"))

    missing = sorted(item for item in requested_set if item not in found)
    if missing:
        msg = f"Entregas confirmadas nao encontradas no dispatch artifact: {missing}"
        raise CloudRunnerError(msg)
    return tuple(found[key] for key in sorted(found))


@contextmanager
def _pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)

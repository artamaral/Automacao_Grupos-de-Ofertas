from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ofertas_bot.google_drive_rules import resolve_rules_file, resolve_sheet_csv_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_REGISTRY_PATH = resolve_rules_file(
    sheet_name="catalog_registry",
    legacy_path=PROJECT_ROOT / "n8n" / "google_sheets_seed" / "catalog_registry.csv",
)


class CatalogRegistryError(ValueError):
    """Raised when the catalog registry is invalid."""


@dataclass(frozen=True)
class CatalogRegistryEntry:
    profile: str
    relative_dir: str
    file_name: str
    drive_file_id: str
    drive_url: str
    active: bool = True

    def __post_init__(self) -> None:
        normalized_profile = self.profile.strip().lower()
        normalized_relative_dir = self.relative_dir.strip().replace("\\", "/").strip("/")
        normalized_file_name = self.file_name.strip()
        normalized_drive_file_id = self.drive_file_id.strip()
        normalized_drive_url = self.drive_url.strip()

        if not normalized_profile:
            raise CatalogRegistryError("catalog registry profile is required")
        if not normalized_relative_dir:
            raise CatalogRegistryError("catalog registry relative_dir is required")
        if not normalized_file_name:
            raise CatalogRegistryError("catalog registry file_name is required")
        if not normalized_drive_file_id:
            raise CatalogRegistryError("catalog registry drive_file_id is required")
        if not normalized_drive_url:
            raise CatalogRegistryError("catalog registry drive_url is required")

        object.__setattr__(self, "profile", normalized_profile)
        object.__setattr__(self, "relative_dir", normalized_relative_dir)
        object.__setattr__(self, "file_name", normalized_file_name)
        object.__setattr__(self, "drive_file_id", normalized_drive_file_id)
        object.__setattr__(self, "drive_url", normalized_drive_url)


def load_catalog_registry(
    path: Path = DEFAULT_CATALOG_REGISTRY_PATH,
) -> dict[str, CatalogRegistryEntry]:
    resolved_path = resolve_sheet_csv_path(path, sheet_name="catalog_registry")
    try:
        with resolved_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except FileNotFoundError as error:
        raise CatalogRegistryError(f"catalog registry file not found: {resolved_path}") from error

    if not rows:
        raise CatalogRegistryError("catalog registry csv must contain at least one row")

    registry: dict[str, CatalogRegistryEntry] = {}
    for row in rows:
        entry = CatalogRegistryEntry(
            profile=row.get("profile", ""),
            relative_dir=row.get("relative_dir", ""),
            file_name=row.get("file_name", ""),
            drive_file_id=row.get("drive_file_id", ""),
            drive_url=row.get("drive_url", ""),
            active=_csv_bool_or_default(row.get("active"), True),
        )
        if entry.profile in registry:
            raise CatalogRegistryError(f"duplicate catalog registry profile: {entry.profile}")
        registry[entry.profile] = entry
    return registry


def resolve_catalog_registry_entry(profile: str) -> CatalogRegistryEntry | None:
    normalized_profile = profile.strip().lower()
    return load_catalog_registry().get(normalized_profile)


def _csv_bool_or_default(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise CatalogRegistryError("catalog registry active is invalid")

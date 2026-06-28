from pathlib import Path

import pytest

from ofertas_bot.catalog_registry import (
    CatalogRegistryError,
    load_catalog_registry,
)


def test_load_catalog_registry_reads_csv_export(tmp_path: Path) -> None:
    path = tmp_path / "catalog_registry.csv"
    path.write_text(
        "\n".join(
            [
                "profile,relative_dir,file_name,drive_file_id,drive_url,active",
                "feminino,feminino,clean_catalog_rating_4_8_plus.csv,file-1,https://drive.google.com/file/d/file-1/view,true",
            ]
        ),
        encoding="utf-8",
    )

    registry = load_catalog_registry(path)

    assert set(registry) == {"feminino"}
    assert registry["feminino"].relative_dir == "feminino"
    assert registry["feminino"].file_name == "clean_catalog_rating_4_8_plus.csv"


def test_load_catalog_registry_rejects_duplicate_profiles(tmp_path: Path) -> None:
    path = tmp_path / "catalog_registry.csv"
    path.write_text(
        "\n".join(
            [
                "profile,relative_dir,file_name,drive_file_id,drive_url,active",
                "feminino,feminino,clean_catalog_rating_4_8_plus.csv,file-1,https://drive.google.com/file/d/file-1/view,true",
                "feminino,feminino,clean_catalog_rating_4_8_plus.csv,file-2,https://drive.google.com/file/d/file-2/view,true",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(CatalogRegistryError, match="duplicate"):
        load_catalog_registry(path)

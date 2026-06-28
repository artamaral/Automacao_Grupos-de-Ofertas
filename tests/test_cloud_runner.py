from pathlib import Path

import pytest

from ofertas_bot import cloud_runner


def test_parse_profiles_accepts_csv_and_deduplicates() -> None:
    profiles = cloud_runner.parse_profiles(profiles_csv="feminino,mae-e-bebe,feminino")

    assert profiles == ("feminino", "mae-e-bebe")


def test_parse_profiles_rejects_invalid_value() -> None:
    with pytest.raises(cloud_runner.CloudRunnerError):
        cloud_runner.parse_profiles(profiles_csv="feminino,invalido")


def test_run_prepare_window_generates_summary(tmp_path, monkeypatch) -> None:
    app_dir = tmp_path / "app"
    config_dir = app_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "discovery_profiles.toml").write_text("", encoding="utf-8")

    catalogs_dir = tmp_path / "catalogs"
    data_dir = tmp_path / "data"
    catalog_path = catalogs_dir / "feminino" / "clean_catalog_rating_4_8_plus.csv"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text("productName,offerLink\nProduto,https://example.com\n", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(argv: list[str]) -> int:
        calls.append(argv)
        target_data_dir = Path(argv[argv.index("--data-dir") + 1])
        target_data_dir.mkdir(parents=True, exist_ok=True)
        (target_data_dir / "offers.json").write_text("[]", encoding="utf-8")
        return 0

    monkeypatch.setattr(cloud_runner.local_flow_cli, "run", fake_run)

    payload = cloud_runner.run_prepare_window(
        profiles_csv="feminino",
        root_dir=str(tmp_path),
        app_dir=str(app_dir),
        catalogs_dir=str(catalogs_dir),
        data_dir=str(data_dir),
        run_id="run-1",
    )

    assert payload["stage"] == "prepare"
    assert payload["total_profiles"] == 1
    assert calls
    assert "--catalog-file" in calls[0]
    assert Path(payload["summary_path"]).exists()


def test_run_finalize_window_generates_summary(tmp_path, monkeypatch) -> None:
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True)
    data_dir = tmp_path / "data"
    profile_dir = data_dir / "feminino"
    profile_dir.mkdir(parents=True)

    calls: list[list[str]] = []

    def fake_run(argv: list[str]) -> int:
        calls.append(argv)
        target_data_dir = Path(argv[argv.index("--data-dir") + 1])
        target_data_dir.mkdir(parents=True, exist_ok=True)
        (target_data_dir / "dispatch_artifact.json").write_text("{}", encoding="utf-8")
        (target_data_dir / "dispatch_report.json").write_text("{}", encoding="utf-8")
        return 0

    monkeypatch.setattr(cloud_runner.local_flow_cli, "run", fake_run)

    payload = cloud_runner.run_finalize_window(
        profiles_csv="feminino",
        root_dir=str(tmp_path),
        app_dir=str(app_dir),
        catalogs_dir=str(tmp_path / "catalogs"),
        data_dir=str(data_dir),
        run_id="run-2",
    )

    assert payload["stage"] == "finalize"
    assert payload["total_profiles"] == 1
    assert calls[0][:2] == ["--stage", "finalize"]
    assert Path(payload["summary_path"]).exists()

from pathlib import Path

import pytest

from ofertas_bot import cloud_runner
from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.storage.json_message_draft_store import message_draft_to_json
from ofertas_bot.storage.json_selection_state_store import (
    JsonSelectionStateStore,
    stamp_selected_offers,
    update_selection_state_from_selected_offers,
)


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
    catalog_path.write_text(
        "productName,offerLink\nProduto,https://example.com\n",
        encoding="utf-8",
    )

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
    assert "--defer-last-sent-at" in calls[0]
    assert Path(payload["summary_path"]).exists()


def test_profile_catalog_path_uses_catalog_registry(tmp_path, monkeypatch) -> None:
    from ofertas_bot import cloud_runner as module

    config = module.CloudPathConfig(
        root_dir=tmp_path,
        app_dir=tmp_path,
        catalogs_dir=tmp_path / "catalogs",
        data_dir=tmp_path / "data",
    )

    class FakeEntry:
        active = True
        relative_dir = "feminino"
        file_name = "clean_catalog_rating_4_8_plus.csv"

    monkeypatch.setattr(module, "resolve_catalog_registry_entry", lambda profile: FakeEntry())

    path = module.profile_catalog_path(config, "feminino")

    assert path == config.catalogs_dir / "feminino" / "clean_catalog_rating_4_8_plus.csv"


def test_load_dispatch_window_filters_allowed_targets(tmp_path) -> None:
    data_dir = tmp_path / "data" / "feminino"
    data_dir.mkdir(parents=True)
    artifact_path = data_dir / "dispatch_artifact.json"
    artifact_path.write_text(
        """
        {
          "targets": [
            {
              "target": "grupo-teste",
              "adapter_kind": "whatsapp",
              "status": "ready",
              "quiet_period_active": false,
              "messages": [
                {
                  "manifest_item_number": 1,
                  "created_at": "2026-06-28T10:00:00-03:00",
                  "planned_at": "2026-06-28T10:00:00-03:00",
                  "planned_offset_seconds": 0,
                  "status": "ready",
                  "text": "Oferta teste",
                  "offer": {"title": "Produto"}
                }
              ]
            },
            {
              "target": "grupo-bloqueado",
              "adapter_kind": "whatsapp",
              "status": "blocked",
              "quiet_period_active": true,
              "messages": []
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    payload = cloud_runner.load_dispatch_window(
        profiles_csv="feminino",
        root_dir=str(tmp_path),
        app_dir=str(tmp_path / "app"),
        catalogs_dir=str(tmp_path / "catalogs"),
        data_dir=str(tmp_path / "data"),
        run_id="run-3",
        allowed_targets_csv="grupo-teste",
    )

    assert payload["stage"] == "dispatch-window"
    assert payload["total_profiles"] == 1
    assert payload["total_targets"] == 1
    assert payload["total_deliveries"] == 1
    assert payload["deliveries"][0]["target"] == "grupo-teste"
    assert payload["allowed_targets"] == ["grupo-teste"]


def test_confirm_window_deliveries_updates_selection_state(tmp_path) -> None:
    data_dir = tmp_path / "data" / "feminino"
    data_dir.mkdir(parents=True)
    offer = Offer(
        marketplace=Marketplace.SHOPEE,
        title="Produto teste",
        url="https://example.com/produto",
        image_url=None,
        price=10,
        old_price=20,
        commission_rate=0.12,
        sales_count=10,
        rating=4.9,
        niche="feminino",
    )
    stamped_offer = stamp_selected_offers(
        [offer],
        selected_at="2026-06-27T10:00:00+00:00",
        cooldown_until="2026-06-28T10:00:00+00:00",
    )[0]
    records = update_selection_state_from_selected_offers({}, [stamped_offer])
    JsonSelectionStateStore(path=data_dir / "selection_state.json").save(records)

    draft = MessageDraft(offer=stamped_offer, text="Oferta teste")
    (data_dir / "dispatch_artifact.json").write_text(
        json_payload(
            {
                "targets": [
                    {
                        "target": "grupo-teste",
                        "adapter_kind": "whatsapp",
                        "messages": [
                            {
                                "manifest_item_number": 1,
                                "draft": message_draft_to_json(draft),
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = cloud_runner.confirm_window_deliveries(
        deliveries=[
            {
                "profile": "feminino",
                "target": "grupo-teste",
                "manifest_item_number": 1,
            }
        ],
        root_dir=str(tmp_path),
        app_dir=str(tmp_path / "app"),
        catalogs_dir=str(tmp_path / "catalogs"),
        data_dir=str(tmp_path / "data"),
        sent_at="2026-06-28T14:00:00+00:00",
    )

    updated = JsonSelectionStateStore(path=data_dir / "selection_state.json").load()
    assert payload["confirmed_count"] == 1
    assert updated[offer.stable_key].last_sent_at == "2026-06-28T14:00:00+00:00"


def json_payload(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, indent=2)

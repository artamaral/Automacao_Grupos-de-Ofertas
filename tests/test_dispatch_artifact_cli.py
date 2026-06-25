import json
from datetime import datetime

from ofertas_bot.dispatch_artifact_cli import build_dispatch_artifact, run
from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.storage.json_publication_manifest_store import (
    JsonPublicationManifestStore,
    PublicationManifestItem,
)


def make_draft(title: str, niche: str = "teste") -> MessageDraft:
    offer = Offer(
        marketplace=Marketplace.MOCK,
        title=title,
        url="https://example.com/produto",
        image_url=None,
        price=10,
        old_price=20,
        commission_rate=0.05,
        sales_count=100,
        rating=4.7,
        niche=niche,
    )
    return MessageDraft(
        offer=offer,
        text="Oferta em português com emoji ✨",
    )


def test_dispatch_artifact_cli_groups_messages_by_target(tmp_path, capsys) -> None:
    manifest_path = tmp_path / "publication_manifest.json"
    artifact_path = tmp_path / "dispatch_artifact.json"
    JsonPublicationManifestStore(path=manifest_path).save(
        (
            PublicationManifestItem(
                draft=make_draft("Produto beleza", niche="beleza"),
                target="grupo-beleza",
                status="ready",
                created_at="2026-06-25T00:00:00+00:00",
                max_messages_per_run=2,
                max_messages_per_hour=2,
                min_interval_seconds=45,
                quiet_periods=("22:00-08:00",),
            ),
            PublicationManifestItem(
                draft=make_draft("Produto auto", niche="auto e moto"),
                target="grupo-auto",
                status="ready",
                created_at="2026-06-25T00:00:00+00:00",
                max_messages_per_run=1,
                max_messages_per_hour=1,
                min_interval_seconds=60,
                quiet_periods=("22:00-08:00",),
            ),
            PublicationManifestItem(
                draft=make_draft("Produto beleza 2", niche="beleza"),
                target="grupo-beleza",
                status="ready",
                created_at="2026-06-25T00:00:00+00:00",
                max_messages_per_run=2,
                max_messages_per_hour=2,
                min_interval_seconds=45,
                quiet_periods=("22:00-08:00",),
            ),
        )
    )

    exit_code = run(
        [
            "--manifest-json",
            str(manifest_path),
            "--save-dispatch-artifact-json",
            str(artifact_path),
        ]
    )

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    output = capsys.readouterr().out
    assert exit_code == 0
    assert payload["timezone"] == "America/Sao_Paulo"
    assert payload["summary"]["total_targets"] == 2
    assert payload["summary"]["total_available_messages"] == 3
    assert payload["summary"]["total_selected_messages"] == 3
    assert payload["summary"]["total_skipped_messages"] == 0
    assert payload["summary"]["total_blocked_targets"] == 0
    assert payload["summary"]["total_messages"] == 3
    assert payload["targets"][0]["target"] == "grupo-auto"
    assert payload["targets"][0]["adapter_kind"] == "whatsapp"
    assert payload["targets"][0]["max_messages_per_run"] == 1
    assert payload["targets"][0]["max_messages_per_hour"] == 1
    assert payload["targets"][0]["min_interval_seconds"] == 60
    assert payload["targets"][0]["quiet_period_active"] is False
    assert payload["targets"][1]["target"] == "grupo-beleza"
    assert payload["targets"][1]["adapter_kind"] == "whatsapp"
    assert payload["targets"][1]["message_count"] == 2
    assert payload["targets"][1]["selected_message_count"] == 2
    assert payload["targets"][1]["skipped_message_count"] == 0
    assert payload["targets"][1]["available_message_count"] == 2
    assert payload["targets"][1]["selection_reason"] is None
    assert payload["targets"][1]["max_messages_per_hour"] == 2
    first_planned_at = datetime.fromisoformat(payload["targets"][1]["first_planned_at"])
    last_planned_at = datetime.fromisoformat(payload["targets"][1]["last_planned_at"])
    second_planned_at = datetime.fromisoformat(payload["targets"][1]["messages"][1]["planned_at"])
    assert first_planned_at.utcoffset() is not None
    assert last_planned_at == second_planned_at
    assert int((last_planned_at - first_planned_at).total_seconds()) == 45
    assert payload["targets"][1]["messages"][1]["planned_offset_seconds"] == 45
    assert payload["targets"][1]["messages"][0]["text"] == "Oferta em português com emoji ✨"
    assert (
        payload["targets"][1]["messages"][0]["draft"]["text"]
        == "Oferta em português com emoji ✨"
    )
    assert "Nenhum envio" in output


def test_dispatch_artifact_cli_blocks_target_during_quiet_period() -> None:
    manifest = (
        PublicationManifestItem(
            draft=make_draft("Produto beleza", niche="beleza"),
            target="grupo-beleza",
            status="ready",
            created_at="2026-06-25T00:00:00+00:00",
            max_messages_per_run=2,
            max_messages_per_hour=2,
            min_interval_seconds=45,
            quiet_periods=("22:00-08:00",),
        ),
    )

    payload = build_dispatch_artifact(
        manifest,
        now=datetime.fromisoformat("2026-06-26T02:00:00+00:00"),
    )

    assert payload["targets"][0]["quiet_period_active"] is True
    assert payload["targets"][0]["status"] == "blocked"
    assert payload["targets"][0]["blocked_reason"] == "quiet_period_active"
    assert payload["targets"][0]["selection_reason"] == "quiet_period_active"
    assert payload["targets"][0]["message_count"] == 0
    assert payload["targets"][0]["selected_message_count"] == 0
    assert payload["targets"][0]["skipped_message_count"] == 1


def test_dispatch_artifact_cli_uses_sao_paulo_timezone_for_quiet_period() -> None:
    manifest = (
        PublicationManifestItem(
            draft=make_draft("Produto beleza", niche="beleza"),
            target="grupo-beleza",
            status="ready",
            created_at="2026-06-25T00:00:00+00:00",
            max_messages_per_run=2,
            max_messages_per_hour=2,
            min_interval_seconds=45,
            quiet_periods=("22:00-08:00",),
        ),
    )

    payload = build_dispatch_artifact(
        manifest,
        now=datetime.fromisoformat("2026-06-26T02:00:00+00:00"),
    )

    assert payload["generated_at"] == "2026-06-25T23:00:00-03:00"
    assert payload["timezone"] == "America/Sao_Paulo"
    assert payload["targets"][0]["quiet_period_active"] is True


def test_dispatch_artifact_cli_blocks_empty_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "publication_manifest.json"
    artifact_path = tmp_path / "dispatch_artifact.json"
    JsonPublicationManifestStore(path=manifest_path).save(())

    exit_code = run(
        [
            "--manifest-json",
            str(manifest_path),
            "--save-dispatch-artifact-json",
            str(artifact_path),
        ]
    )

    assert exit_code == 3
    assert not artifact_path.exists()

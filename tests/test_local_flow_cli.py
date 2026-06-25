from pathlib import Path

from ofertas_bot import local_flow_cli
from ofertas_bot.models import Marketplace, MessageDraft, Offer
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
    MessageReviewRouting,
)
from ofertas_bot.storage.json_offer_store import JsonOfferStore


def _seed_prepare_outputs(tmp_path: Path, niche: str = "beleza") -> None:
    offer = Offer(
        marketplace=Marketplace.MOCK,
        title="Produto teste",
        url="https://example.com/produto",
        image_url=None,
        price=10,
        old_price=20,
        commission_rate=0.05,
        sales_count=100,
        rating=4.7,
        niche=niche,
    )
    draft = MessageDraft(
        offer=offer,
        text="Link de afiliado com comissão: https://example.com/produto",
    )
    JsonOfferStore(path=tmp_path / "offers.json").save([offer])
    JsonMessageReviewQueueStore(path=tmp_path / "review_queue.json").save(
        (
            MessageReviewQueueItem(
                draft=draft,
                status="pending",
                routing=MessageReviewRouting(
                    group_slug="beleza-ofertas",
                    group_name="Beleza Ofertas",
                    destination_kind="group",
                    destination_ref="grupo-beleza",
                    message_tone="direto",
                ),
            ),
        )
    )


def test_local_flow_prepare_uses_default_paths(tmp_path, monkeypatch, capsys) -> None:
    calls: list[list[str]] = []

    def fake_harness_run(argv: list[str]) -> int:
        calls.append(argv)
        _seed_prepare_outputs(tmp_path)
        return 0

    monkeypatch.setattr(local_flow_cli.harness, "run", fake_harness_run)

    exit_code = local_flow_cli.run(
        [
            "--stage",
            "prepare",
            "--target",
            "grupo-maquiagem",
            "--data-dir",
            str(tmp_path),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls
    assert str(tmp_path / "review_queue.json") in calls[0]
    assert str(tmp_path / "messages.json") in calls[0]
    assert str(tmp_path / "messages.txt") in calls[0]
    assert (tmp_path / "review_plan.json").exists()
    assert (tmp_path / "review_plan.txt").exists()
    assert "Etapa prepare concluída" in output


def test_local_flow_finalize_runs_steps_in_order(tmp_path, monkeypatch) -> None:
    order: list[str] = []
    manifest_calls: list[list[str]] = []
    export_calls: list[list[str]] = []
    dispatch_calls: list[list[str]] = []
    dispatch_execute_calls: list[list[str]] = []
    bundle_calls: list[list[str]] = []
    doctor_calls: list[list[str]] = []

    def make_step(name: str):
        def fake_run(argv: list[str]) -> int:
            order.append(name)
            if name == "export":
                export_calls.append(argv)
            if name == "manifest":
                manifest_calls.append(argv)
            if name == "dispatch":
                dispatch_calls.append(argv)
            if name == "dispatch-execute":
                dispatch_execute_calls.append(argv)
            if name == "bundle":
                bundle_calls.append(argv)
            if name == "doctor":
                doctor_calls.append(argv)
            assert argv
            return 0

        return fake_run

    monkeypatch.setattr(local_flow_cli.review_queue_export_cli, "run", make_step("export"))
    monkeypatch.setattr(local_flow_cli.publication_manifest_cli, "run", make_step("manifest"))
    monkeypatch.setattr(
        local_flow_cli.publication_manifest_validate_cli,
        "run",
        make_step("validate"),
    )
    monkeypatch.setattr(local_flow_cli.dispatch_artifact_cli, "run", make_step("dispatch"))
    monkeypatch.setattr(
        local_flow_cli.dispatch_execute_cli,
        "run",
        make_step("dispatch-execute"),
    )
    monkeypatch.setattr(local_flow_cli.local_review_bundle_cli, "run", make_step("bundle"))
    monkeypatch.setattr(local_flow_cli.local_artifacts_doctor_cli, "run", make_step("doctor"))

    exit_code = local_flow_cli.run(
        [
            "--stage",
            "finalize",
            "--data-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert order == [
        "export",
        "manifest",
        "validate",
        "dispatch",
        "dispatch-execute",
        "bundle",
        "doctor",
    ]
    assert "--queue-json" in manifest_calls[0]
    assert "--target" not in manifest_calls[0]
    assert "--save-approved-messages-by-group-dir" in export_calls[0]
    assert str(tmp_path / "approved_messages_by_group") in export_calls[0]
    assert "--save-dispatch-artifact-json" in dispatch_calls[0]
    assert str(tmp_path / "dispatch_artifact.json") in dispatch_calls[0]
    assert "--save-dispatch-report-json" in dispatch_execute_calls[0]
    assert str(tmp_path / "dispatch_report.json") in dispatch_execute_calls[0]
    assert "--save-dispatch-report-text" in dispatch_execute_calls[0]
    assert str(tmp_path / "dispatch_report.txt") in dispatch_execute_calls[0]
    assert "--dispatch-artifact-json" in bundle_calls[0]
    assert str(tmp_path / "dispatch_artifact.json") in bundle_calls[0]
    assert "--dispatch-report-json" in bundle_calls[0]
    assert str(tmp_path / "dispatch_report.json") in bundle_calls[0]
    assert "--dispatch-artifact-json" in doctor_calls[0]
    assert "--dispatch-report-json" in doctor_calls[0]


def test_local_flow_prepare_prefers_profile_and_generates_review_plan(
    tmp_path, monkeypatch
) -> None:
    calls: list[list[str]] = []

    def fake_harness_run(argv: list[str]) -> int:
        calls.append(argv)
        _seed_prepare_outputs(tmp_path, niche="beleza")
        return 0

    monkeypatch.setattr(local_flow_cli.harness, "run", fake_harness_run)

    profiles_path = tmp_path / "profiles.toml"
    profiles_path.write_text(
        """
[[profiles]]
slug = "beleza"
name = "Beleza"
niche = "beleza"
marketplace = "mock"
target = "grupo-beleza"
""".strip(),
        encoding="utf-8",
    )

    exit_code = local_flow_cli.run(
        [
            "--stage",
            "prepare",
            "--profile",
            "beleza",
            "--profiles-file",
            str(profiles_path),
            "--data-dir",
            str(tmp_path),
        ]
    )

    review_plan_json = (tmp_path / "review_plan.json").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "--profile" in calls[0]
    assert "beleza" in calls[0]
    assert "beleza-ofertas" in review_plan_json


def test_local_flow_finalize_stops_on_first_error(tmp_path, monkeypatch) -> None:
    order: list[str] = []

    def fake_export_run(argv: list[str]) -> int:
        order.append("export")
        assert argv
        return 3

    def fake_manifest_run(argv: list[str]) -> int:
        order.append("manifest")
        assert argv
        return 0

    monkeypatch.setattr(local_flow_cli.review_queue_export_cli, "run", fake_export_run)
    monkeypatch.setattr(local_flow_cli.publication_manifest_cli, "run", fake_manifest_run)
    monkeypatch.setattr(local_flow_cli.dispatch_artifact_cli, "run", fake_manifest_run)
    monkeypatch.setattr(local_flow_cli.dispatch_execute_cli, "run", fake_manifest_run)

    exit_code = local_flow_cli.run(
        [
            "--stage",
            "finalize",
            "--data-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 3
    assert order == ["export"]


def test_local_flow_prepare_requires_target(tmp_path) -> None:
    exit_code = local_flow_cli.run(
        [
            "--stage",
            "prepare",
            "--data-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 3


def test_local_flow_paths_uses_data_dir(tmp_path) -> None:
    paths = local_flow_cli.LocalFlowPaths(data_dir=tmp_path)

    assert paths.offers_json == Path(tmp_path / "offers.json")
    assert paths.review_queue_json == Path(tmp_path / "review_queue.json")
    assert paths.approved_messages_json == Path(tmp_path / "approved_messages.json")
    assert paths.approved_messages_by_group_dir == Path(tmp_path / "approved_messages_by_group")
    assert paths.dispatch_artifact_json == Path(tmp_path / "dispatch_artifact.json")
    assert paths.dispatch_report_json == Path(tmp_path / "dispatch_report.json")
    assert paths.dispatch_report_text == Path(tmp_path / "dispatch_report.txt")
    assert paths.manifest_json == Path(tmp_path / "publication_manifest.json")
    assert paths.bundle_json == Path(tmp_path / "local_review_bundle.json")
    assert paths.review_plan_json == Path(tmp_path / "review_plan.json")
    assert paths.review_plan_text == Path(tmp_path / "review_plan.txt")

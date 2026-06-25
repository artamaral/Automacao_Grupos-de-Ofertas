from pathlib import Path

from ofertas_bot import local_flow_cli


def test_local_flow_prepare_uses_default_paths(tmp_path, monkeypatch, capsys) -> None:
    calls: list[list[str]] = []

    def fake_harness_run(argv: list[str]) -> int:
        calls.append(argv)
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
    assert "Etapa prepare concluída" in output


def test_local_flow_finalize_runs_steps_in_order(tmp_path, monkeypatch) -> None:
    order: list[str] = []
    manifest_calls: list[list[str]] = []

    def make_step(name: str):
        def fake_run(argv: list[str]) -> int:
            order.append(name)
            if name == "manifest":
                manifest_calls.append(argv)
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
    assert order == ["export", "manifest", "validate", "bundle", "doctor"]
    assert "--queue-json" in manifest_calls[0]
    assert "--target" not in manifest_calls[0]


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
    assert paths.manifest_json == Path(tmp_path / "publication_manifest.json")
    assert paths.bundle_json == Path(tmp_path / "local_review_bundle.json")

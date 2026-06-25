import json

from ofertas_bot.dispatch_execute_cli import run


def test_dispatch_execute_cli_generates_dry_run_report(tmp_path, capsys) -> None:
    artifact_path = tmp_path / "dispatch_artifact.json"
    report_path = tmp_path / "dispatch_report.json"
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-25T00:00:00+00:00",
                "summary": {"total_targets": 2, "total_messages": 3},
                "targets": [
                    {
                        "target": "grupo-auto",
                        "adapter_kind": "whatsapp",
                        "status": "ready",
                        "message_count": 1,
                        "messages": [
                            {
                                "manifest_item_number": 1,
                                "status": "ready",
                                "created_at": "2026-06-25T00:00:00+00:00",
                                "text": "Auto com comissão 🚗",
                                "draft": {
                                    "offer": {
                                        "marketplace": "mock",
                                        "title": "Produto auto",
                                        "url": "https://example.com/auto",
                                        "image_url": None,
                                        "price": 10,
                                        "old_price": 20,
                                        "commission_rate": 0.05,
                                        "sales_count": 100,
                                        "rating": 4.7,
                                        "niche": "auto e moto",
                                        "is_prime_or_free_shipping": False,
                                    },
                                    "text": "Auto com comissão 🚗",
                                },
                                "offer": {
                                    "marketplace": "mock",
                                    "niche": "auto e moto",
                                    "title": "Produto auto",
                                    "url": "https://example.com/auto",
                                    "price": 10,
                                    "old_price": 20,
                                },
                            }
                        ],
                    },
                    {
                        "target": "grupo-beleza",
                        "adapter_kind": "whatsapp",
                        "status": "ready",
                        "message_count": 2,
                        "messages": [
                            {
                                "manifest_item_number": 2,
                                "status": "ready",
                                "created_at": "2026-06-25T00:00:00+00:00",
                                "text": "Beleza com comissão ✨",
                                "draft": {
                                    "offer": {
                                        "marketplace": "mock",
                                        "title": "Produto beleza",
                                        "url": "https://example.com/beleza",
                                        "image_url": None,
                                        "price": 15,
                                        "old_price": 30,
                                        "commission_rate": 0.05,
                                        "sales_count": 100,
                                        "rating": 4.7,
                                        "niche": "beleza",
                                        "is_prime_or_free_shipping": False,
                                    },
                                    "text": "Beleza com comissão ✨",
                                },
                                "offer": {
                                    "marketplace": "mock",
                                    "niche": "beleza",
                                    "title": "Produto beleza",
                                    "url": "https://example.com/beleza",
                                    "price": 15,
                                    "old_price": 30,
                                },
                            },
                            {
                                "manifest_item_number": 3,
                                "status": "ready",
                                "created_at": "2026-06-25T00:00:00+00:00",
                                "text": "Skincare com comissão 💄",
                                "draft": {
                                    "offer": {
                                        "marketplace": "mock",
                                        "title": "Produto skincare",
                                        "url": "https://example.com/skincare",
                                        "image_url": None,
                                        "price": 25,
                                        "old_price": 40,
                                        "commission_rate": 0.05,
                                        "sales_count": 100,
                                        "rating": 4.7,
                                        "niche": "beleza",
                                        "is_prime_or_free_shipping": False,
                                    },
                                    "text": "Skincare com comissão 💄",
                                },
                                "offer": {
                                    "marketplace": "mock",
                                    "niche": "beleza",
                                    "title": "Produto skincare",
                                    "url": "https://example.com/skincare",
                                    "price": 25,
                                    "old_price": 40,
                                },
                            },
                        ],
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    exit_code = run(
        [
            "--dispatch-artifact-json",
            str(artifact_path),
            "--save-dispatch-report-json",
            str(report_path),
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    output = capsys.readouterr().out
    assert exit_code == 0
    assert payload["mode"] == "dry-run"
    assert payload["adapter_kind"] == "whatsapp"
    assert payload["summary"]["total_targets"] == 2
    assert payload["summary"]["total_messages"] == 3
    assert payload["summary"]["total_sent"] == 0
    assert payload["summary"]["total_dry_run"] == 3
    assert payload["targets"][1]["target"] == "grupo-beleza"
    assert payload["targets"][1]["adapter_kind"] == "whatsapp"
    assert payload["targets"][1]["dry_run_messages"] == 2
    assert payload["targets"][1]["messages"][0]["delivery_label"] == "whatsapp:grupo-beleza"
    assert payload["targets"][1]["messages"][0]["text"] == "Beleza com comissão ✨"
    assert "Nenhum envio real" in output


def test_dispatch_execute_cli_accepts_telegram_adapter(tmp_path) -> None:
    artifact_path = tmp_path / "dispatch_artifact.json"
    report_path = tmp_path / "dispatch_report.json"
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-25T00:00:00+00:00",
                "targets": [
                    {
                        "target": "canal-telegram",
                        "adapter_kind": "telegram",
                        "status": "ready",
                        "message_count": 1,
                        "messages": [
                            {
                                "manifest_item_number": 1,
                                "status": "ready",
                                "created_at": "2026-06-25T00:00:00+00:00",
                                "text": "Telegram com comissão 📣",
                                "draft": {
                                    "offer": {
                                        "marketplace": "mock",
                                        "title": "Produto telegram",
                                        "url": "https://example.com/telegram",
                                        "image_url": None,
                                        "price": 10,
                                        "old_price": 20,
                                        "commission_rate": 0.05,
                                        "sales_count": 100,
                                        "rating": 4.7,
                                        "niche": "achadinhos geral",
                                        "is_prime_or_free_shipping": False,
                                    },
                                    "text": "Telegram com comissão 📣",
                                },
                                "offer": {
                                    "marketplace": "mock",
                                    "niche": "achadinhos geral",
                                    "title": "Produto telegram",
                                    "url": "https://example.com/telegram",
                                    "price": 10,
                                    "old_price": 20,
                                },
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    exit_code = run(
        [
            "--dispatch-artifact-json",
            str(artifact_path),
            "--save-dispatch-report-json",
            str(report_path),
            "--adapter-kind",
            "telegram",
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["adapter_kind"] == "telegram"
    assert payload["targets"][0]["messages"][0]["delivery_label"] == "telegram:canal-telegram"


def test_dispatch_execute_cli_blocks_empty_targets(tmp_path) -> None:
    artifact_path = tmp_path / "dispatch_artifact.json"
    report_path = tmp_path / "dispatch_report.json"
    artifact_path.write_text(
        json.dumps({"generated_at": "2026-06-25T00:00:00+00:00", "targets": []}),
        encoding="utf-8",
    )

    exit_code = run(
        [
            "--dispatch-artifact-json",
            str(artifact_path),
            "--save-dispatch-report-json",
            str(report_path),
        ]
    )

    assert exit_code == 3
    assert not report_path.exists()

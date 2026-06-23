from ofertas_bot.group_plan import format_group_plan_summary


def test_format_group_plan_summary_returns_text() -> None:
    summary = {
        "total_groups": 1,
        "allowed_groups": 1,
        "blocked_groups": 0,
        "total_selected_offers": 2,
        "metadata": {
            "niche": "maquiagem",
            "generated_at": "2026-06-23T18:00:00+00:00",
            "offer_limit": 2,
            "collected_offer_count": 2,
            "source_marketplace": "mock",
        },
        "groups": [
            {
                "group_slug": "maquiagem-vip",
                "allowed": True,
                "selected_offer_count": 2,
                "reasons": [],
                "next_available_at": None,
            }
        ],
    }

    text = format_group_plan_summary(summary)

    assert "Resumo do plano por grupo" in text
    assert "metadata.niche=maquiagem" in text
    assert "group=maquiagem-vip" in text
    assert "selected_offer_count=2" in text

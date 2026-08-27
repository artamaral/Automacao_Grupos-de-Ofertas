from __future__ import annotations

from datetime import date
from pathlib import Path

from ofertas_bot.distribution_strategy import resolve_profile_distribution_strategy


def test_legacy_distribution_strategy_preserves_bands(tmp_path: Path) -> None:
    path = tmp_path / "selection_profiles.toml"
    path.write_text(
        """
[[policies]]
slug = "mae e bebe"
niche = "mae e bebe"
total_items = 2
max_zero_sales_items = 1
minimum_daily_runs = 1
cooldown_hours_default = 24
evidence = "catalog.csv"

[[policies.bands]]
subniche = "mamadeiras"
share_percent = 50
items = 1

[[policies.bands]]
subniche = "fraldas"
share_percent = 50
items = 1
""",
        encoding="utf-8",
    )

    strategy = resolve_profile_distribution_strategy(
        "mae e bebe",
        operational_date=date(2026, 8, 27),
        path=path,
    )

    assert strategy.planning_mode == "bands"
    assert strategy.refresh_weights == {"mamadeiras": 1, "fraldas": 1}
    assert strategy.required_daily_quotas == strategy.refresh_weights


def test_daily_persisted_strategy_uses_fixed_quota_missing_from_bands(
    tmp_path: Path,
) -> None:
    path = tmp_path / "selection_profiles.toml"
    path.write_text(
        """
[[policies]]
slug = "feminino"
niche = "feminino"
total_items = 3
max_zero_sales_items = 1
minimum_daily_runs = 1
cooldown_hours_default = 24
evidence = "catalog.csv"
planning_mode = "daily_persisted"
daily_total_items = 3
rotation_items_per_day = 1
schedule_hours = [8]
max_items_per_subniche_per_window = 3

[[policies.bands]]
subniche = "maquiagem-olhos"
share_percent = 100
items = 3

[[policies.fixed_daily_quotas]]
subniche = "calcados-sandalia"
items = 2

[[policies.weekly_rotation_quotas]]
subniche = "maquiagem-pele"
items = 7
""",
        encoding="utf-8",
    )

    strategy = resolve_profile_distribution_strategy(
        "feminino",
        operational_date=date(2026, 8, 27),
        path=path,
    )

    assert strategy.planning_mode == "daily_persisted"
    assert strategy.required_daily_quotas == {
        "calcados-sandalia": 2,
        "maquiagem-pele": 1,
    }
    assert "maquiagem-olhos" not in strategy.refresh_weights
    assert strategy.refresh_weights["calcados-sandalia"] == 2


def test_feminino_strategy_includes_required_calcados_subniches() -> None:
    strategy = resolve_profile_distribution_strategy(
        "feminino",
        operational_date=date(2026, 8, 27),
    )

    assert {
        key: strategy.refresh_weights[key]
        for key in (
            "calcados-sandalia",
            "calcados-sapatilha",
            "calcados-chinelo",
            "calcados-rasteirinha",
            "calcados-mocassim",
        )
    } == {
        "calcados-sandalia": 10,
        "calcados-sapatilha": 8,
        "calcados-chinelo": 4,
        "calcados-rasteirinha": 4,
        "calcados-mocassim": 2,
    }

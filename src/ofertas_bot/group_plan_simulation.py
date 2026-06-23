from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ofertas_bot.agents.collector import CollectorAgent
from ofertas_bot.group_plan import (
    GroupPlan,
    GroupPlanBuilder,
    format_group_plan_summary,
    summarize_group_plans,
)
from ofertas_bot.group_plan_naming import build_group_plan_file_prefix
from ofertas_bot.group_plan_validation import normalize_plan_niche, validate_plan_limit
from ofertas_bot.group_profiles import GroupProfileCatalog
from ofertas_bot.models import Marketplace
from ofertas_bot.settings import Settings
from ofertas_bot.storage.json_group_plan_store import JsonGroupPlanStore


class GroupPlanTextWriteError(OSError):
    """Raised when a group plan text summary cannot be written."""


@dataclass(frozen=True)
class GroupPlanSimulationResult:
    plans: tuple[GroupPlan, ...]
    summary: dict[str, Any]

    def to_text(self) -> str:
        return format_group_plan_summary(self.summary)

    def save_json(self, path: Path) -> None:
        JsonGroupPlanStore(path=path).save(self.summary)

    def save_text(self, path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.to_text(), encoding="utf-8")
        except OSError as error:
            msg = f"Could not write group plan text to {path}"
            raise GroupPlanTextWriteError(msg) from error


class GroupPlanSimulation:
    def __init__(
        self,
        *,
        settings: Settings,
        catalog: GroupProfileCatalog,
        collector: CollectorAgent | None = None,
        plan_builder: GroupPlanBuilder | None = None,
    ) -> None:
        self.settings = settings
        self.catalog = catalog
        self.collector = collector or CollectorAgent(settings=settings)
        self.plan_builder = plan_builder or GroupPlanBuilder()

    def build(
        self,
        *,
        niche: str,
        now: datetime,
        limit: int | None = None,
        last_runs_by_group: dict[str, datetime | None] | None = None,
    ) -> GroupPlanSimulationResult:
        normalized_niche = normalize_plan_niche(niche)
        offer_limit = validate_plan_limit(
            limit if limit is not None else self.settings.max_offers_per_run
        )
        offers = self.collector.collect(
            marketplace=Marketplace.MOCK,
            niche=normalized_niche,
            limit=offer_limit,
        )
        plans = self.plan_builder.build_plans(
            group_profiles=self.catalog.active_profiles(),
            offers=offers,
            now=now,
            last_runs_by_group=last_runs_by_group,
        )
        summary = summarize_group_plans(plans)
        summary["metadata"] = {
            "niche": normalized_niche,
            "generated_at": now.isoformat(),
            "file_prefix": build_group_plan_file_prefix(
                niche=normalized_niche,
                generated_at=now,
            ),
            "offer_limit": offer_limit,
            "collected_offer_count": len(offers),
            "source_marketplace": Marketplace.MOCK.value,
        }
        return GroupPlanSimulationResult(
            plans=plans,
            summary=summary,
        )

    def save_summary(
        self,
        *,
        summary: dict[str, Any],
        path: Path,
    ) -> None:
        JsonGroupPlanStore(path=path).save(summary)

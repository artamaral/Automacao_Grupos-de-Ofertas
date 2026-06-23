from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ofertas_bot.agents.collector import CollectorAgent
from ofertas_bot.group_plan import GroupPlan, GroupPlanBuilder, summarize_group_plans
from ofertas_bot.group_profiles import GroupProfileCatalog
from ofertas_bot.models import Marketplace
from ofertas_bot.settings import Settings
from ofertas_bot.storage.json_group_plan_store import JsonGroupPlanStore


@dataclass(frozen=True)
class GroupPlanSimulationResult:
    plans: tuple[GroupPlan, ...]
    summary: dict[str, Any]


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
        offer_limit = limit if limit is not None else self.settings.max_offers_per_run
        offers = self.collector.collect(
            marketplace=Marketplace.MOCK,
            niche=niche,
            limit=offer_limit,
        )
        plans = self.plan_builder.build_plans(
            group_profiles=self.catalog.active_profiles(),
            offers=offers,
            now=now,
            last_runs_by_group=last_runs_by_group,
        )
        return GroupPlanSimulationResult(
            plans=plans,
            summary=summarize_group_plans(plans),
        )

    def save_summary(
        self,
        *,
        summary: dict[str, Any],
        path: Path,
    ) -> None:
        JsonGroupPlanStore(path=path).save(summary)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ofertas_bot.group_plan import GroupPlan


@dataclass(frozen=True)
class GroupPlanApproval:
    approved: bool
    reviewer: str
    reviewed_at: datetime
    notes: str = ""


@dataclass(frozen=True)
class GroupPlanApprovalResult:
    approved: bool
    plans: tuple[GroupPlan, ...]
    reasons: tuple[str, ...]


class GroupPlanApprovalGate:
    def evaluate(
        self,
        *,
        plans: tuple[GroupPlan, ...],
        approval: GroupPlanApproval | None,
    ) -> GroupPlanApprovalResult:
        if approval is None:
            return GroupPlanApprovalResult(
                approved=False,
                plans=(),
                reasons=("aprovacao humana ausente",),
            )
        if not approval.approved:
            return GroupPlanApprovalResult(
                approved=False,
                plans=(),
                reasons=("aprovacao humana negada",),
            )
        if not approval.reviewer.strip():
            return GroupPlanApprovalResult(
                approved=False,
                plans=(),
                reasons=("revisor da aprovacao humana ausente",),
            )

        approved_plans = tuple(plan for plan in plans if plan.allowed)
        if not approved_plans:
            return GroupPlanApprovalResult(
                approved=False,
                plans=(),
                reasons=("nenhum plano permitido para aprovacao",),
            )

        return GroupPlanApprovalResult(
            approved=True,
            plans=approved_plans,
            reasons=(),
        )

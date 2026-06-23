from __future__ import annotations

from typing import Any

from ofertas_bot.group_plan_approval import GroupPlanApproval, GroupPlanApprovalResult


def summarize_group_plan_approval(
    *,
    approval: GroupPlanApproval | None,
    result: GroupPlanApprovalResult,
) -> dict[str, Any]:
    return {
        "approved": result.approved,
        "reviewer": approval.reviewer.strip() if approval else None,
        "reviewed_at": approval.reviewed_at.isoformat() if approval else None,
        "notes": approval.notes.strip() if approval and approval.notes else "",
        "approved_group_count": len(result.plans),
        "approved_groups": [plan.group_slug for plan in result.plans],
        "reasons": list(result.reasons),
    }

from datetime import UTC, datetime

from ofertas_bot.group_plan import GroupPlan
from ofertas_bot.group_plan_approval import GroupPlanApproval, GroupPlanApprovalResult
from ofertas_bot.group_plan_approval_summary import summarize_group_plan_approval


def test_summarize_group_plan_approval_with_approved_result() -> None:
    reviewed_at = datetime(2026, 6, 23, 18, 0, tzinfo=UTC)
    approval = GroupPlanApproval(
        approved=True,
        reviewer=" arthur ",
        reviewed_at=reviewed_at,
        notes=" aprovado ",
    )
    plan = GroupPlan(
        group_slug="maquiagem-vip",
        allowed=True,
        selected_offers=(),
        reasons=(),
    )
    result = GroupPlanApprovalResult(approved=True, plans=(plan,), reasons=())

    summary = summarize_group_plan_approval(approval=approval, result=result)

    assert summary == {
        "approved": True,
        "reviewer": "arthur",
        "reviewed_at": "2026-06-23T18:00:00+00:00",
        "notes": "aprovado",
        "approved_group_count": 1,
        "approved_groups": ["maquiagem-vip"],
        "reasons": [],
    }


def test_summarize_group_plan_approval_without_approval() -> None:
    result = GroupPlanApprovalResult(
        approved=False,
        plans=(),
        reasons=("aprovacao humana ausente",),
    )

    summary = summarize_group_plan_approval(approval=None, result=result)

    assert summary == {
        "approved": False,
        "reviewer": None,
        "reviewed_at": None,
        "notes": "",
        "approved_group_count": 0,
        "approved_groups": [],
        "reasons": ["aprovacao humana ausente"],
    }

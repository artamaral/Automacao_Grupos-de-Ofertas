from datetime import UTC, datetime

from ofertas_bot.group_plan import GroupPlan
from ofertas_bot.group_plan_approval import GroupPlanApproval, GroupPlanApprovalGate


def test_group_plan_approval_gate_requires_approval() -> None:
    result = GroupPlanApprovalGate().evaluate(plans=(), approval=None)

    assert not result.approved
    assert result.reasons == ("aprovacao humana ausente",)


def test_group_plan_approval_gate_rejects_denied_approval() -> None:
    approval = GroupPlanApproval(
        approved=False,
        reviewer="arthur",
        reviewed_at=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
    )

    result = GroupPlanApprovalGate().evaluate(plans=(), approval=approval)

    assert not result.approved
    assert result.reasons == ("aprovacao humana negada",)


def test_group_plan_approval_gate_requires_reviewer() -> None:
    approval = GroupPlanApproval(
        approved=True,
        reviewer="   ",
        reviewed_at=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
    )

    result = GroupPlanApprovalGate().evaluate(plans=(), approval=approval)

    assert not result.approved
    assert result.reasons == ("revisor da aprovacao humana ausente",)


def test_group_plan_approval_gate_returns_only_allowed_plans() -> None:
    approval = GroupPlanApproval(
        approved=True,
        reviewer="arthur",
        reviewed_at=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
    )
    allowed_plan = GroupPlan(
        group_slug="maquiagem-vip",
        allowed=True,
        selected_offers=(),
        reasons=(),
    )
    blocked_plan = GroupPlan(
        group_slug="casa-vip",
        allowed=False,
        selected_offers=(),
        reasons=("bloqueado",),
    )

    result = GroupPlanApprovalGate().evaluate(
        plans=(allowed_plan, blocked_plan),
        approval=approval,
    )

    assert result.approved
    assert result.plans == (allowed_plan,)
    assert result.reasons == ()


def test_group_plan_approval_gate_rejects_without_allowed_plans() -> None:
    approval = GroupPlanApproval(
        approved=True,
        reviewer="arthur",
        reviewed_at=datetime(2026, 6, 23, 18, 0, tzinfo=UTC),
    )
    blocked_plan = GroupPlan(
        group_slug="casa-vip",
        allowed=False,
        selected_offers=(),
        reasons=("bloqueado",),
    )

    result = GroupPlanApprovalGate().evaluate(
        plans=(blocked_plan,),
        approval=approval,
    )

    assert not result.approved
    assert result.reasons == ("nenhum plano permitido para aprovacao",)

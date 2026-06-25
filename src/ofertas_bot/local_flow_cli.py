from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ofertas_bot import (
    dispatch_artifact_cli,
    harness,
    local_artifacts_doctor_cli,
    local_review_bundle_cli,
    publication_manifest_cli,
    publication_manifest_validate_cli,
    review_queue_export_cli,
)
from ofertas_bot.discovery_profiles import (
    DiscoveryProfile,
    DiscoveryProfileError,
    load_discovery_profile_catalog,
)
from ofertas_bot.group_plan import GroupPlanBuilder
from ofertas_bot.group_profiles import DEFAULT_GROUP_PROFILES, GroupProfile, GroupProfileCatalog
from ofertas_bot.models import Marketplace, Offer
from ofertas_bot.storage.json_group_plan_store import JsonGroupPlanStore
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    summarize_review_queue,
)
from ofertas_bot.storage.json_offer_store import JsonOfferStore, OfferStoreError


@dataclass(frozen=True)
class LocalFlowPaths:
    data_dir: Path

    @property
    def offers_json(self) -> Path:
        return self.data_dir / "offers.json"

    @property
    def messages_json(self) -> Path:
        return self.data_dir / "messages.json"

    @property
    def messages_text(self) -> Path:
        return self.data_dir / "messages.txt"

    @property
    def review_queue_json(self) -> Path:
        return self.data_dir / "review_queue.json"

    @property
    def approved_messages_json(self) -> Path:
        return self.data_dir / "approved_messages.json"

    @property
    def approved_messages_text(self) -> Path:
        return self.data_dir / "approved_messages.txt"

    @property
    def approved_messages_by_group_dir(self) -> Path:
        return self.data_dir / "approved_messages_by_group"

    @property
    def dispatch_artifact_json(self) -> Path:
        return self.data_dir / "dispatch_artifact.json"

    @property
    def manifest_json(self) -> Path:
        return self.data_dir / "publication_manifest.json"

    @property
    def bundle_json(self) -> Path:
        return self.data_dir / "local_review_bundle.json"

    @property
    def review_plan_json(self) -> Path:
        return self.data_dir / "review_plan.json"

    @property
    def review_plan_text(self) -> Path:
        return self.data_dir / "review_plan.txt"


@dataclass(frozen=True)
class PrepareContext:
    profile: DiscoveryProfile | None
    subgroup_slug: str | None
    niche: str
    marketplace: Marketplace
    target: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Orquestra o fluxo local seguro")
    parser.add_argument(
        "--stage",
        choices=("prepare", "finalize"),
        required=True,
        help="Etapa operacional: prepare gera fila; finalize consolida aprovadas",
    )
    parser.add_argument(
        "--niche",
        default="maquiagem",
        help="Nicho usado na etapa prepare",
    )
    parser.add_argument(
        "--marketplace",
        choices=[item.value for item in Marketplace],
        default=Marketplace.MOCK.value,
        help="Marketplace usado na etapa prepare",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Profile versionado usado na etapa prepare",
    )
    parser.add_argument(
        "--subgroup",
        default=None,
        help="Subgrupo opcional do profile usado na etapa prepare",
    )
    parser.add_argument(
        "--profiles-file",
        default="config/discovery_profiles.toml",
        help="Arquivo TOML com profiles de descoberta",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Alvo opt-in lógico usado nos artefatos locais",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Quantidade máxima de ofertas na etapa prepare",
    )
    parser.add_argument(
        "--data-dir",
        default=".data",
        help="Diretório local padrão dos artefatos",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = LocalFlowPaths(data_dir=Path(args.data_dir))
    paths.data_dir.mkdir(parents=True, exist_ok=True)

    if args.stage == "prepare":
        return _run_prepare(args=args, paths=paths)
    if args.stage == "finalize":
        return _run_finalize(args=args, paths=paths)

    print("ERRO | Etapa operacional desconhecida", file=sys.stderr)
    return 3


def _run_prepare(*, args: argparse.Namespace, paths: LocalFlowPaths) -> int:
    prepare_context = _resolve_prepare_context(args)
    if isinstance(prepare_context, int):
        return prepare_context
    print("INFO | Iniciando fluxo local: prepare")
    exit_code = harness.run(
        _build_prepare_harness_args(args=args, paths=paths, context=prepare_context)
    )
    if exit_code != 0:
        return exit_code

    try:
        review_plan = _build_review_plan(paths=paths, context=prepare_context)
        JsonGroupPlanStore(path=paths.review_plan_json).save(review_plan)
        paths.review_plan_text.write_text(
            _format_review_plan_text(review_plan),
            encoding="utf-8",
        )
    except (DiscoveryProfileError, OfferStoreError, OSError, ValueError) as error:
        return _print_review_plan_error(error)

    print("INFO | Etapa prepare concluída.")
    print(f"INFO | Fila local: {paths.review_queue_json}")
    print(f"INFO | Plano da rodada JSON: {paths.review_plan_json}")
    print(f"INFO | Plano da rodada TXT: {paths.review_plan_text}")
    print("AÇÃO | Atualize a fila para approved/rejected antes da etapa finalize.")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _run_finalize(*, args: argparse.Namespace, paths: LocalFlowPaths) -> int:
    print("INFO | Iniciando fluxo local: finalize")

    step_exit_code = review_queue_export_cli.run(
        [
            "--queue-json",
            str(paths.review_queue_json),
            "--save-approved-messages-json",
            str(paths.approved_messages_json),
            "--save-approved-messages-text",
            str(paths.approved_messages_text),
            "--save-approved-messages-by-group-dir",
            str(paths.approved_messages_by_group_dir),
        ]
    )
    if step_exit_code != 0:
        return _print_finalize_step_error("exportar aprovadas", step_exit_code)

    step_exit_code = publication_manifest_cli.run(
        [
            "--queue-json",
            str(paths.review_queue_json),
            "--save-publication-manifest-json",
            str(paths.manifest_json),
        ]
    )
    if step_exit_code != 0:
        return _print_finalize_step_error("gerar manifesto", step_exit_code)

    step_exit_code = publication_manifest_validate_cli.run(
        [
            "--publication-manifest-json",
            str(paths.manifest_json),
        ]
    )
    if step_exit_code != 0:
        return _print_finalize_step_error("validar manifesto", step_exit_code)

    step_exit_code = dispatch_artifact_cli.run(
        [
            "--manifest-json",
            str(paths.manifest_json),
            "--save-dispatch-artifact-json",
            str(paths.dispatch_artifact_json),
        ]
    )
    if step_exit_code != 0:
        return _print_finalize_step_error("gerar artefato de disparo", step_exit_code)

    step_exit_code = local_review_bundle_cli.run(
        [
            "--queue-json",
            str(paths.review_queue_json),
            "--approved-messages-json",
            str(paths.approved_messages_json),
            "--manifest-json",
            str(paths.manifest_json),
            "--save-bundle-json",
            str(paths.bundle_json),
        ]
    )
    if step_exit_code != 0:
        return _print_finalize_step_error("gerar bundle local", step_exit_code)

    step_exit_code = local_artifacts_doctor_cli.run(
        [
            "--queue-json",
            str(paths.review_queue_json),
            "--approved-json",
            str(paths.approved_messages_json),
            "--manifest-json",
            str(paths.manifest_json),
            "--bundle-json",
            str(paths.bundle_json),
        ]
    )
    if step_exit_code != 0:
        return _print_finalize_step_error("executar doctor local", step_exit_code)

    print("INFO | Etapa finalize concluída.")
    print(f"INFO | Aprovadas por grupo: {paths.approved_messages_by_group_dir}")
    print(f"INFO | Artefato de disparo: {paths.dispatch_artifact_json}")
    print(f"INFO | Bundle local: {paths.bundle_json}")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _resolve_prepare_context(args: argparse.Namespace) -> PrepareContext | int:
    if args.profile:
        try:
            profile = load_discovery_profile_catalog(Path(args.profiles_file)).get(args.profile)
        except DiscoveryProfileError as error:
            return _print_prepare_context_error(error)
        if profile is None:
            return _print_prepare_context_error(
                DiscoveryProfileError(f"profile nao encontrado: {args.profile}")
            )
        subgroup_slug = None
        if args.subgroup:
            subgroup_slug = str(args.subgroup).strip().lower()
            try:
                profile.scoped_to_subgroup(subgroup_slug)
            except DiscoveryProfileError as error:
                return _print_prepare_context_error(error)
        target = str(args.target or profile.target or "").strip()
        if not target:
            return _print_missing_prepare_target()
        return PrepareContext(
            profile=profile,
            subgroup_slug=subgroup_slug,
            niche=profile.niche,
            marketplace=profile.marketplace,
            target=target,
        )

    if not args.target:
        return _print_missing_prepare_target()
    return PrepareContext(
        profile=None,
        subgroup_slug=None,
        niche=str(args.niche).strip().lower(),
        marketplace=Marketplace(str(args.marketplace)),
        target=str(args.target).strip(),
    )


def _build_prepare_harness_args(
    *,
    args: argparse.Namespace,
    paths: LocalFlowPaths,
    context: PrepareContext,
) -> list[str]:
    command = ["--dry-run"]
    if context.profile is not None:
        command.extend(
            [
                "--profile",
                context.profile.slug,
                "--profiles-file",
                str(args.profiles_file),
            ]
        )
        if context.subgroup_slug:
            command.extend(["--subgroup", context.subgroup_slug])
        if args.target:
            command.extend(["--target", context.target])
        if args.limit is not None:
            command.extend(["--limit", str(args.limit)])
    else:
        command.extend(
            [
                "--niche",
                context.niche,
                "--marketplace",
                context.marketplace.value,
                "--limit",
                str(args.limit),
                "--target",
                context.target,
            ]
        )

    command.extend(
        [
            "--save-json",
            str(paths.offers_json),
            "--save-messages-json",
            str(paths.messages_json),
            "--save-messages-text",
            str(paths.messages_text),
            "--save-review-queue-json",
            str(paths.review_queue_json),
        ]
    )
    return command


def _build_review_plan(
    *,
    paths: LocalFlowPaths,
    context: PrepareContext,
) -> dict[str, Any]:
    offers = JsonOfferStore(path=paths.offers_json).load()
    queue_items = JsonMessageReviewQueueStore(path=paths.review_queue_json).load()
    now = datetime.now(UTC).replace(microsecond=0)
    group_profiles = _matching_group_profiles(
        catalog=DEFAULT_GROUP_PROFILES,
        niche=context.niche,
        marketplace=context.marketplace,
    )
    plans = GroupPlanBuilder().build_plans(
        group_profiles=group_profiles,
        offers=offers,
        now=now,
    )
    queue_summary = summarize_review_queue(queue_items)
    groups: list[dict[str, Any]] = []

    for profile in group_profiles:
        plan = next((item for item in plans if item.group_slug == profile.slug), None)
        selected_offers = tuple(plan.selected_offers) if plan is not None else ()
        groups.append(
            {
                "group_slug": profile.slug,
                "group_name": profile.name,
                "destination_ref": profile.destination_ref,
                "destination_kind": profile.destination_kind,
                "message_tone": profile.message_tone,
                "allowed": bool(plan.allowed) if plan is not None else False,
                "selected_offer_count": len(selected_offers),
                "selected_offers": [_offer_snapshot(offer) for offer in selected_offers],
                "review_queue_items": _count_review_queue_items(queue_items, profile.slug),
                "reasons": list(plan.reasons) if plan is not None else [],
                "next_available_at": plan.next_available_at.isoformat()
                if plan is not None and plan.next_available_at is not None
                else None,
            }
        )

    return {
        "metadata": {
            "generated_at": now.isoformat(),
            "profile_slug": context.profile.slug if context.profile is not None else None,
            "subgroup_slug": context.subgroup_slug,
            "niche": context.niche,
            "marketplace": context.marketplace.value,
            "target": context.target,
            "offers_path": str(paths.offers_json),
            "review_queue_path": str(paths.review_queue_json),
        },
        "summary": {
            "total_groups": len(group_profiles),
            "allowed_groups": sum(1 for group in groups if group["allowed"]),
            "blocked_groups": sum(1 for group in groups if not group["allowed"]),
            "total_offers_collected": len(offers),
            "total_selected_offers": sum(group["selected_offer_count"] for group in groups),
            "total_review_queue_items": queue_summary["total"],
            "total_routed_queue_items": queue_summary["routed"],
            "total_unrouted_queue_items": queue_summary["unrouted"],
        },
        "review_queue": dict(queue_summary),
        "groups": groups,
    }


def _matching_group_profiles(
    *,
    catalog: GroupProfileCatalog,
    niche: str,
    marketplace: Marketplace,
) -> tuple[GroupProfile, ...]:
    return tuple(
        profile
        for profile in catalog.active_profiles()
        if profile.allows_niche(niche) and profile.allows_marketplace(marketplace)
    )


def _count_review_queue_items(queue_items: tuple[Any, ...], group_slug: str) -> int:
    return sum(
        1
        for item in queue_items
        if item.routing is not None and item.routing.group_slug == group_slug
    )


def _offer_snapshot(offer: Offer) -> dict[str, Any]:
    return {
        "title": offer.title,
        "url": offer.url,
        "price": offer.price,
        "old_price": offer.old_price,
        "niche": offer.niche,
        "marketplace": offer.marketplace.value,
    }


def _format_review_plan_text(review_plan: dict[str, Any]) -> str:
    metadata = review_plan.get("metadata", {})
    summary = review_plan.get("summary", {})
    groups = review_plan.get("groups", [])
    lines = [
        "Plano da rodada",
        f"profile={metadata.get('profile_slug')}",
        f"subgroup={metadata.get('subgroup_slug')}",
        f"niche={metadata.get('niche')}",
        f"marketplace={metadata.get('marketplace')}",
        f"generated_at={metadata.get('generated_at')}",
        f"total_groups={summary.get('total_groups')}",
        f"allowed_groups={summary.get('allowed_groups')}",
        f"blocked_groups={summary.get('blocked_groups')}",
        f"total_offers_collected={summary.get('total_offers_collected')}",
        f"total_selected_offers={summary.get('total_selected_offers')}",
        f"total_review_queue_items={summary.get('total_review_queue_items')}",
    ]
    for group in groups:
        lines.extend(
            [
                "-" * 80,
                f"group={group.get('group_slug')}",
                f"name={group.get('group_name')}",
                f"allowed={group.get('allowed')}",
                f"destination_ref={group.get('destination_ref')}",
                f"message_tone={group.get('message_tone')}",
                f"selected_offer_count={group.get('selected_offer_count')}",
                f"review_queue_items={group.get('review_queue_items')}",
            ]
        )
        reasons = group.get("reasons")
        if isinstance(reasons, list) and reasons:
            lines.append(f"reasons={'; '.join(str(item) for item in reasons)}")
        selected_offers = group.get("selected_offers")
        if isinstance(selected_offers, list):
            for offer in selected_offers:
                if isinstance(offer, dict):
                    lines.append(
                        f"offer={offer.get('title')} | price={offer.get('price')} | "
                        f"marketplace={offer.get('marketplace')}"
                    )
    return "\n".join(lines) + "\n"


def _print_finalize_step_error(step_name: str, exit_code: int) -> int:
    print(f"ERRO | Etapa finalize falhou em: {step_name}", file=sys.stderr)
    print("INFO | Nenhum envio foi executado.")
    return exit_code


def _print_missing_prepare_target() -> int:
    print("ERRO | Etapa prepare requer --target ou um profile com target", file=sys.stderr)
    print("INFO | Nenhum envio foi executado.")
    return 3


def _print_prepare_context_error(error: Exception) -> int:
    print("ERRO | Contexto de prepare invalido", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("INFO | Nenhum envio foi executado.")
    return 3


def _print_review_plan_error(error: Exception) -> int:
    print("ERRO | Nao foi possivel gerar o plano da rodada", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("INFO | Nenhum envio foi executado.")
    return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

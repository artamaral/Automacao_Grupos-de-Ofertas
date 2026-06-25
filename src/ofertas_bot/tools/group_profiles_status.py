from __future__ import annotations

import argparse
from collections.abc import Sequence

from ofertas_bot.group_profiles import DEFAULT_GROUP_PROFILES, GroupProfile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lista perfis de grupos e nichos configurados")
    parser.add_argument(
        "--niche",
        default=None,
        help="Filtra perfis ativos por nicho",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        default=False,
        help="Inclui perfis inativos na listagem sem executar ações externas",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = DEFAULT_GROUP_PROFILES

    if args.niche:
        profiles = catalog.profiles_for_niche(args.niche)
        print("INFO | Perfis ativos compatíveis com nicho")
        print(f"INFO | niche={args.niche.strip().lower()}")
    elif args.include_inactive:
        profiles = catalog.profiles
        print("INFO | Perfis cadastrados")
    else:
        profiles = catalog.active_profiles()
        print("INFO | Perfis ativos cadastrados")

    if not profiles:
        print("INFO | Nenhum perfil encontrado para os filtros informados.")
        print("INFO | Nenhuma chamada externa foi executada.")
        print("INFO | Nenhuma publicação foi executada.")
        return 0

    for profile in profiles:
        _print_profile(profile)

    print("INFO | Nenhuma chamada externa foi executada.")
    print("INFO | Nenhuma publicação foi executada.")
    return 0


def _print_profile(profile: GroupProfile) -> None:
    niches = ",".join(profile.allowed_niches)
    marketplaces = ",".join(item.value for item in profile.allowed_marketplaces)
    content_types = ",".join(profile.allowed_content_types)
    print("-" * 80)
    print(f"INFO | group={profile.slug}")
    print(f"INFO | name={profile.name}")
    print(f"INFO | active={profile.active}")
    print(f"INFO | allowed_niches={niches}")
    print(f"INFO | allowed_marketplaces={marketplaces}")
    print(f"INFO | destination_kind={profile.destination_kind}")
    print(f"INFO | destination_ref={profile.destination_ref}")
    print(f"INFO | message_tone={profile.message_tone}")
    print(f"INFO | allowed_content_types={content_types}")
    print(f"INFO | max_offers_per_run={profile.max_offers_per_run}")
    print(f"INFO | min_minutes_between_posts={profile.min_minutes_between_posts}")


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

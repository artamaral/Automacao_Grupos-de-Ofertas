from __future__ import annotations

import argparse
from pathlib import Path

from ofertas_bot.offline_post_generator import OfflinePostGenerator
from ofertas_bot.product_resolver import ShopeeProductResolver
from ofertas_bot.settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ofertas-post-from-url",
        description="Gera posts offline a partir de uma URL de produto da Shopee.",
    )
    parser.add_argument("url", help="URL completa ou curta de produto da Shopee")
    parser.add_argument("--reels", action="store_true", help="Gera Reel 9:16 e legenda")
    parser.add_argument("--carousel", action="store_true", help="Gera carrossel e legenda")
    parser.add_argument(
        "--story",
        action="store_true",
        help="Gera Story com area para Link Sticker",
    )
    parser.add_argument("--all", action="store_true", help="Gera reels, carousel e story")
    parser.add_argument("--output", type=Path, default=Path("output"), help="Diretorio de saida")
    parser.add_argument("--preview", action="store_true", help="Gera preview.html local")
    return parser


def selected_formats(args: argparse.Namespace) -> tuple[str, ...]:
    if args.all:
        return ("reels", "carousel", "story")
    formats: list[str] = []
    if args.reels:
        formats.append("reels")
    if args.carousel:
        formats.append("carousel")
    if args.story:
        formats.append("story")
    if not formats:
        raise ValueError("Informe --reels, --carousel, --story ou --all.")
    return tuple(formats)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        formats = selected_formats(args)
    except ValueError as exc:
        parser.error(str(exc))

    settings = get_settings()
    product = ShopeeProductResolver(settings=settings).resolve(args.url)
    package = OfflinePostGenerator().generate(
        product,
        formats=formats,
        output_dir=args.output,
        preview=args.preview,
    )
    print(package.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ofertas_bot import (
    harness,
    local_artifacts_doctor_cli,
    local_review_bundle_cli,
    publication_manifest_cli,
    publication_manifest_validate_cli,
    review_queue_export_cli,
)
from ofertas_bot.models import Marketplace


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
    def manifest_json(self) -> Path:
        return self.data_dir / "publication_manifest.json"

    @property
    def bundle_json(self) -> Path:
        return self.data_dir / "local_review_bundle.json"


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
        "--target",
        required=True,
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
    print("INFO | Iniciando fluxo local: prepare")
    exit_code = harness.run(
        [
            "--niche",
            args.niche,
            "--marketplace",
            args.marketplace,
            "--limit",
            str(args.limit),
            "--target",
            args.target,
            "--dry-run",
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
    if exit_code != 0:
        return exit_code

    print("INFO | Etapa prepare concluída.")
    print(f"INFO | Fila local: {paths.review_queue_json}")
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
        ]
    )
    if step_exit_code != 0:
        return _print_finalize_step_error("exportar aprovadas", step_exit_code)

    step_exit_code = publication_manifest_cli.run(
        [
            "--approved-messages-json",
            str(paths.approved_messages_json),
            "--target",
            args.target,
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
    print(f"INFO | Bundle local: {paths.bundle_json}")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _print_finalize_step_error(step_name: str, exit_code: int) -> int:
    print(f"ERRO | Etapa finalize falhou em: {step_name}", file=sys.stderr)
    print("INFO | Nenhum envio foi executado.")
    return exit_code


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

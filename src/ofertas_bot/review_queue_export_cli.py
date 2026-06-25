from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ofertas_bot.storage.json_message_draft_store import (
    JsonMessageDraftStore,
    MessageDraftStoreWriteError,
)
from ofertas_bot.storage.json_message_review_queue_store import (
    JsonMessageReviewQueueStore,
    MessageReviewQueueItem,
    MessageReviewQueueStoreError,
    approved_review_drafts,
    summarize_review_queue,
)

REVIEW_TEXT_ENCODING = "utf-8-sig"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exporta mensagens aprovadas da fila")
    parser.add_argument(
        "--queue-json",
        required=True,
        help="Caminho do arquivo local review_queue.json",
    )
    parser.add_argument(
        "--save-approved-messages-json",
        default=None,
        help="Caminho local para salvar mensagens aprovadas em JSON",
    )
    parser.add_argument(
        "--save-approved-messages-text",
        default=None,
        help="Caminho local para salvar mensagens aprovadas em texto",
    )
    parser.add_argument(
        "--save-approved-messages-by-group-dir",
        default=None,
        help="Diretorio local para salvar mensagens aprovadas separadas por grupo",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if (
        not args.save_approved_messages_json
        and not args.save_approved_messages_text
        and not args.save_approved_messages_by_group_dir
    ):
        return _print_missing_output_error()

    queue_store = JsonMessageReviewQueueStore(path=Path(args.queue_json))

    try:
        queue_items = queue_store.load()
        summary = summarize_review_queue(queue_items)
        if summary["pending"] > 0:
            return _print_gate_pending_error()
        if summary["approved"] == 0:
            return _print_gate_no_approved_error()

        approved_drafts = approved_review_drafts(queue_items)
        if args.save_approved_messages_json:
            JsonMessageDraftStore(path=Path(args.save_approved_messages_json)).save(
                approved_drafts
            )
            print(
                "INFO | Mensagens aprovadas exportadas em "
                f"{args.save_approved_messages_json}"
            )
        if args.save_approved_messages_text:
            save_path = Path(args.save_approved_messages_text)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(
                format_review_queue_items_for_export(queue_items),
                encoding=REVIEW_TEXT_ENCODING,
            )
            print(f"INFO | Revisão aprovada salva em {save_path}")
        if args.save_approved_messages_by_group_dir:
            saved_groups = export_review_queue_items_by_group(
                queue_items=queue_items,
                output_dir=Path(args.save_approved_messages_by_group_dir),
            )
            print(
                "INFO | Mensagens aprovadas por grupo salvas em "
                f"{args.save_approved_messages_by_group_dir}"
            )
            print(f"INFO | Total de grupos exportados: {saved_groups}")
    except (MessageReviewQueueStoreError, MessageDraftStoreWriteError, OSError) as error:
        return _print_export_error(error=error)

    print(f"INFO | Total de mensagens aprovadas exportadas: {len(approved_drafts)}")
    print("INFO | Nenhum envio foi executado.")
    return 0


def _print_missing_output_error() -> int:
    print("ERRO | Nenhum destino de exportação informado", file=sys.stderr)
    print(
        "AÇÃO | Use --save-approved-messages-json, "
        "--save-approved-messages-text e/ou "
        "--save-approved-messages-by-group-dir.",
        file=sys.stderr,
    )
    return 3


def _print_gate_pending_error() -> int:
    print("ERRO | Exportação bloqueada: ainda existem itens pendentes.", file=sys.stderr)
    print("AÇÃO | Aprove ou rejeite todos os itens antes de exportar.", file=sys.stderr)
    return 3


def _print_gate_no_approved_error() -> int:
    print("ERRO | Exportação bloqueada: nenhuma mensagem aprovada.", file=sys.stderr)
    print("AÇÃO | Aprove ao menos uma mensagem antes de exportar.", file=sys.stderr)
    return 3


def _print_export_error(error: Exception) -> int:
    print("ERRO | Não foi possível exportar mensagens aprovadas", file=sys.stderr)
    print(f"DETALHE | {error}", file=sys.stderr)
    print("AÇÃO | Verifique caminhos e formato da fila.", file=sys.stderr)
    return 3


def format_review_queue_items_for_export(
    items: tuple[MessageReviewQueueItem, ...],
) -> str:
    approved_items = [item for item in items if item.status == "approved"]
    if not approved_items:
        return "Nenhuma mensagem aprovada para revisao.\n"

    blocks = [
        _format_review_queue_item_for_export(index=index, item=item)
        for index, item in enumerate(approved_items, start=1)
    ]
    return "\n\n".join(blocks) + "\n"


def export_review_queue_items_by_group(
    *,
    queue_items: tuple[MessageReviewQueueItem, ...],
    output_dir: Path,
) -> int:
    grouped_items = approved_review_queue_items_by_group(queue_items)
    output_dir.mkdir(parents=True, exist_ok=True)

    for group_slug, items in grouped_items.items():
        drafts = tuple(item.draft for item in items)
        JsonMessageDraftStore(path=output_dir / f"{group_slug}.json").save(drafts)
        (output_dir / f"{group_slug}.txt").write_text(
            format_review_queue_items_for_export(items),
            encoding=REVIEW_TEXT_ENCODING,
        )

    return len(grouped_items)


def approved_review_queue_items_by_group(
    items: tuple[MessageReviewQueueItem, ...],
) -> dict[str, tuple[MessageReviewQueueItem, ...]]:
    grouped_items: dict[str, list[MessageReviewQueueItem]] = {}
    for item in items:
        if item.status != "approved" or item.routing is None:
            continue
        grouped_items.setdefault(item.routing.group_slug, []).append(item)

    return {
        group_slug: tuple(group_items)
        for group_slug, group_items in sorted(grouped_items.items())
    }


def _format_review_queue_item_for_export(
    *,
    index: int,
    item: MessageReviewQueueItem,
) -> str:
    offer = item.draft.offer
    routing = item.routing
    price_line = (
        f"Preco: R$ {offer.price:.2f}"
        if offer.price > 0
        else "Preco: consulte o valor atualizado no link da oferta"
    )
    lines = [
        f"# Mensagem {index}",
        f"Marketplace: {offer.marketplace.value}",
        f"Nicho: {offer.niche}",
        f"Oferta: {offer.title}",
        price_line,
        f"Link: {offer.url}",
    ]
    if routing is not None:
        lines.extend(
            [
                f"Grupo: {routing.group_name}",
                f"Group slug: {routing.group_slug}",
                f"Destino: {routing.destination_kind}:{routing.destination_ref or '-'}",
                f"Canal: {routing.channel_adapter}",
                f"Tom: {routing.message_tone}",
            ]
        )
    lines.extend(["", item.draft.text])
    return "\n".join(lines)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

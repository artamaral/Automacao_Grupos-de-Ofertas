from __future__ import annotations

from ofertas_bot.models import ComplianceResult, MessageDraft
from ofertas_bot.settings import Settings


class ComplianceAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate(self, draft: MessageDraft, dry_run: bool) -> ComplianceResult:
        reasons: list[str] = []
        text = draft.text.lower()

        if not draft.offer.url:
            reasons.append("oferta sem link")

        if draft.offer.price <= 0:
            reasons.append("preço inválido")

        if "afiliado" not in text and "comissão" not in text:
            reasons.append("mensagem sem aviso de afiliado")

        if not dry_run and not self.settings.enable_real_publish:
            reasons.append("publicação real desabilitada por configuração")

        return ComplianceResult(approved=not reasons, reasons=reasons)

    def validate_batch(
        self,
        drafts: tuple[MessageDraft, ...],
        dry_run: bool,
    ) -> tuple[ComplianceResult, ...]:
        return tuple(self.validate(draft=draft, dry_run=dry_run) for draft in drafts)

    def approved_drafts(
        self,
        drafts: tuple[MessageDraft, ...],
        dry_run: bool,
    ) -> tuple[MessageDraft, ...]:
        results = self.validate_batch(drafts=drafts, dry_run=dry_run)
        return tuple(
            draft
            for draft, result in zip(drafts, results, strict=True)
            if result.approved
        )

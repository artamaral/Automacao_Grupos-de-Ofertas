from __future__ import annotations

from ofertas_bot.models import MessageDraft, PublishResult


class DryRunPublisher:
    def publish(self, draft: MessageDraft, target: str) -> PublishResult:
        return PublishResult(sent=False, dry_run=True, target=target, message=draft.text)

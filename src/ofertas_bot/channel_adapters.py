from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ofertas_bot.agents.publisher import DryRunPublisher
from ofertas_bot.models import MessageDraft

ChannelAdapterKind = Literal["console", "whatsapp", "telegram"]


@dataclass(frozen=True)
class ChannelPublishResult:
    adapter_kind: ChannelAdapterKind
    sent: bool
    dry_run: bool
    target: str
    message: str
    delivery_label: str


class ChannelAdapterError(ValueError):
    """Raised when a channel adapter kind is unsupported."""


class BaseDryRunChannelAdapter:
    kind: ChannelAdapterKind

    def __init__(self) -> None:
        self._publisher = DryRunPublisher()

    def publish(self, draft: MessageDraft, target: str) -> ChannelPublishResult:
        result = self._publisher.publish(draft=draft, target=target)
        return ChannelPublishResult(
            adapter_kind=self.kind,
            sent=result.sent,
            dry_run=result.dry_run,
            target=result.target,
            message=result.message,
            delivery_label=self._build_delivery_label(target),
        )

    def _build_delivery_label(self, target: str) -> str:
        return f"{self.kind}:{target}"


class ConsoleDryRunAdapter(BaseDryRunChannelAdapter):
    kind: ChannelAdapterKind = "console"


class WhatsAppDryRunAdapter(BaseDryRunChannelAdapter):
    kind: ChannelAdapterKind = "whatsapp"


class TelegramDryRunAdapter(BaseDryRunChannelAdapter):
    kind: ChannelAdapterKind = "telegram"


def build_channel_adapter(kind: str) -> BaseDryRunChannelAdapter:
    normalized_kind = kind.strip().lower()
    if normalized_kind == "console":
        return ConsoleDryRunAdapter()
    if normalized_kind == "whatsapp":
        return WhatsAppDryRunAdapter()
    if normalized_kind == "telegram":
        return TelegramDryRunAdapter()
    raise ChannelAdapterError(f"unsupported channel adapter: {kind}")

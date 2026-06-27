# ruff: noqa: E501, I001
from __future__ import annotations

import html
import tomllib
from pathlib import Path

from ofertas_bot.models import Marketplace, MessageDraft, ScoredOffer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE_DIR = PROJECT_ROOT / "config" / "message_templates"
DEFAULT_COUPON_URLS_PATH = PROJECT_ROOT / "config" / "coupon_urls.toml"


def render_shopee_message_template(
    scored_offer: ScoredOffer,
    *,
    template_dir: Path = DEFAULT_TEMPLATE_DIR,
    coupon_urls_path: Path = DEFAULT_COUPON_URLS_PATH,
) -> str:
    offer = scored_offer.offer
    template_text = _load_shopee_template(template_dir=template_dir, niche=offer.niche)
    coupon_url = _load_global_coupon_url(path=coupon_urls_path)
    replacements = {
        "{{facts.title}}": offer.title,
        "{{facts.marketplace}}": "Shopee",
        "{{facts.price | brl}}": _format_brl(offer.price),
        "{{facts.discount_percent | round}}": str(round(offer.discount_percent)),
        "{{facts.rating | rating_br}}": _format_rating_br(offer.rating),
        "{{coupon_url}}": coupon_url,
        "{{facts.url}}": offer.url,
    }
    rendered = template_text
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def render_message_preview_html(
    drafts: tuple[MessageDraft, ...],
    *,
    title: str = "Preview da rodada",
    subtitle: str = "prévia da mensagem",
    coupon_urls_path: Path = DEFAULT_COUPON_URLS_PATH,
) -> str:
    coupon_url = _load_global_coupon_url(path=coupon_urls_path)
    cards = "\n".join(
        _render_preview_card(
            draft=draft,
            index=index,
            group_title=title,
            subtitle=subtitle,
            coupon_url=coupon_url,
        )
        for index, draft in enumerate(drafts, start=1)
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0b141a;
      --panel: #111b21;
      --card: #202c33;
      --text: #e9edef;
      --muted: #8696a0;
      --link: #53bdeb;
      --green-soft: #103529;
      --gold: #ffd279;
      --border: #2a3942;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, sans-serif; background: var(--bg); color: var(--text); }}
    .page {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
    .header {{ margin-bottom: 20px; }}
    .header h1 {{ margin: 0 0 6px; font-size: 28px; }}
    .header p {{ margin: 0; color: var(--muted); font-size: 14px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
    .phone {{ background: #10181d; border: 1px solid var(--border); border-radius: 24px; padding: 12px; box-shadow: 0 16px 40px rgba(0,0,0,0.28); }}
    .phone-top {{ display: flex; align-items: center; gap: 10px; padding: 8px 8px 14px; }}
    .avatar {{ width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center; background: #ffb21c; color: #1a1a1a; font-size: 18px; }}
    .group-meta strong, .group-meta span {{ display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .group-meta span {{ margin-top: 2px; color: var(--muted); font-size: 12px; }}
    .bubble {{ background: var(--card); border-radius: 14px; padding: 12px; border: 1px solid rgba(255,255,255,0.03); }}
    .bubble img {{ width: 100%; aspect-ratio: 1 / 1; object-fit: cover; display: block; border-radius: 10px; background: #fff; }}
    .message-body {{ margin-top: 14px; }}
    .title {{ margin: 0 0 12px; font-size: 17px; line-height: 1.3; font-weight: 700; }}
    .line {{ margin: 10px 0 0; font-size: 15px; line-height: 1.4; }}
    .label {{ font-weight: 700; }}
    .price {{ color: #d7fdd3; font-size: 16px; font-weight: 700; }}
    .old-price {{ display: block; margin-top: 6px; color: var(--muted); text-decoration: line-through; text-decoration-thickness: 1px; }}
    .badge {{ display: inline-flex; align-items: center; gap: 6px; margin-top: 8px; border-radius: 999px; background: var(--green-soft); color: #d7fdd3; border: 1px solid rgba(0,168,132,0.35); padding: 5px 10px; font-size: 14px; font-weight: 700; }}
    .rating {{ color: var(--gold); font-weight: 700; }}
    a {{ color: var(--link); text-decoration: none; word-break: break-all; }}
    .ad {{ margin-top: 14px; font-weight: 700; }}
    .time {{ margin-top: 8px; text-align: right; color: var(--muted); font-size: 12px; }}
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <h1>{html.escape(title)}</h1>
      <p>Preview HTML gerado automaticamente a partir da rodada.</p>
    </div>
    <div class="grid">
      {cards}
    </div>
  </div>
</body>
</html>
"""


def _render_preview_card(
    *,
    draft: MessageDraft,
    index: int,
    group_title: str,
    subtitle: str,
    coupon_url: str,
) -> str:
    offer = draft.offer
    marketplace_label = offer.marketplace.value.title()
    if offer.marketplace is not Marketplace.SHOPEE:
        return f"""
      <section class="phone">
        <div class="phone-top">
          <div class="avatar">🛍️</div>
          <div class="group-meta">
            <strong>{html.escape(group_title)}</strong>
            <span>{html.escape(subtitle)} #{index}</span>
          </div>
        </div>
        <article class="bubble">
          <div class="message-body">
            <p class="title">{html.escape(offer.title)}</p>
            <p class="line"><span class="label">Marketplace:</span> {html.escape(marketplace_label)}</p>
            <p class="line">{html.escape(draft.text).replace(chr(10), "<br>")}</p>
          </div>
        </article>
      </section>
"""
    old_price_html = ""
    if offer.old_price and offer.old_price > offer.price:
        old_price_html = f'<span class="old-price">{html.escape(_format_brl(offer.old_price))}</span>'
    image_html = ""
    if offer.image_url:
        image_html = (
            f'<img src="{html.escape(offer.image_url)}" alt="{html.escape(offer.title)}">'
        )
    return f"""
      <section class="phone">
        <div class="phone-top">
          <div class="avatar">🛍️</div>
          <div class="group-meta">
            <strong>{html.escape(group_title)}</strong>
            <span>{html.escape(subtitle)} #{index}</span>
          </div>
        </div>
        <article class="bubble">
          {image_html}
          <div class="message-body">
            <p class="title">🔥 {html.escape(offer.title)}</p>
            <p class="line"><span class="label">🏪 Loja:</span> {html.escape(marketplace_label)}</p>
            <p class="line price">💵 {html.escape(_format_brl(offer.price))} {old_price_html}</p>
            <div class="badge">🏷️ {round(offer.discount_percent)}% OFF</div>
            <p class="line rating">⭐ Avaliação: {html.escape(_format_rating_br(offer.rating))}/5</p>
            <p class="line"><span class="label">🎟️ Resgate o cupom desta página:</span><br><a href="{html.escape(coupon_url)}">{html.escape(coupon_url)}</a></p>
            <p class="line"><span class="label">✅ Link do produto:</span><br><a href="{html.escape(offer.url)}">{html.escape(offer.url)}</a></p>
            <p class="line">Aviso: link de afiliado; podemos receber comissão pela compra. Preço e disponibilidade podem mudar.</p>
            <p class="ad">(anúncio)</p>
          </div>
        </article>
      </section>
"""


def _load_shopee_template(*, template_dir: Path, niche: str) -> str:
    niche_slug = niche.strip().lower().replace(" ", "-")
    candidates = (
        template_dir / f"{niche_slug}.txt",
        template_dir / "shopee.txt",
        template_dir / "mae-e-bebe.txt",
    )
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError("no Shopee message template found")


def _load_global_coupon_url(*, path: Path) -> str:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    coupon_url = payload.get("global_coupon_url")
    if not isinstance(coupon_url, str) or not coupon_url.strip():
        raise ValueError("global_coupon_url is required")
    return coupon_url.strip()


def _format_brl(value: float) -> str:
    rendered = f"{value:,.2f}"
    return "R$ " + rendered.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_rating_br(value: float | None) -> str:
    if value is None:
        return "0,0"
    return f"{value:.1f}".replace(".", ",")

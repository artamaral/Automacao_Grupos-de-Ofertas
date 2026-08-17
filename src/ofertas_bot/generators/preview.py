from __future__ import annotations

import html
from pathlib import Path

from ofertas_bot.product_resolver import ProductData


def generate_preview(
    path: Path,
    product: ProductData,
    *,
    formats: tuple[str, ...],
    caption: str,
) -> None:
    sections: list[str] = []
    if "story" in formats:
        sections.append('<section><h2>Story</h2><img src="story/story.jpg" alt="Story"></section>')
    if "carousel" in formats:
        images = "".join(
            f'<img src="carousel/{index:02d}.jpg" alt="Carrossel {index}">'
            for index in range(1, 5)
        )
        sections.append(f'<section><h2>Carrossel</h2><div class="row">{images}</div></section>')
    if "reels" in formats:
        sections.append(
            '<section><h2>Reel</h2><video controls src="reels/reel.mp4"></video>'
            '<p><a href="reels/reel.mp4">Abrir video</a></p></section>'
        )
    body = "\n".join(sections)
    document = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Preview offline - {html.escape(product.title)}</title>
<style>body{{font-family:Arial,sans-serif;max-width:1200px;margin:auto;padding:24px;background:#111;color:#eee}}section{{margin:28px 0}}img,video{{max-width:320px;max-height:570px;object-fit:contain;background:#fff;margin:6px}}.row{{display:flex;gap:10px;overflow:auto}}textarea{{width:100%;min-height:220px}}button{{padding:10px 14px;margin:6px 6px 6px 0}}</style></head>
<body><h1>{html.escape(product.title)}</h1>{body}
<h2>Legenda oficial</h2><textarea id="caption" readonly>{html.escape(caption)}</textarea><br><button onclick="copyText('caption')">Copiar legenda</button>
<h2>Link afiliado</h2><textarea id="link" readonly>{html.escape(product.affiliate_url)}</textarea><br><button onclick="copyText('link')">Copiar link</button>
<script>function copyText(id){{const el=document.getElementById(id);navigator.clipboard.writeText(el.value);}}</script></body></html>"""
    path.write_text(document, encoding="utf-8")

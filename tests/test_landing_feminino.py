from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_HTML = ROOT / "deploy" / "public_html"
LANDING = PUBLIC_HTML / "feminino" / "index.html"
SCRIPT = PUBLIC_HTML / "assets" / "js" / "feminino.js"
REDIRECT = PUBLIC_HTML / "go" / "whatsapp" / "feminino" / "index.php"
CONFIG = PUBLIC_HTML / "_config" / "whatsapp.php"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_production_package_has_only_expected_top_level_surfaces() -> None:
    assert {path.name for path in PUBLIC_HTML.iterdir()} == {
        ".htaccess",
        "_config",
        "assets",
        "error",
        "feminino",
        "go",
    }
    assert not any(
        path.name in {".git", ".env", "docs", "node_modules", "tests"}
        for path in PUBLIC_HTML.rglob("*")
    )


def test_landing_contains_approved_copy_and_section_order() -> None:
    html = read(LANDING)
    required_copy = [
        "Ofertas e cupons para mulheres, não perca tempo procurando",
        "Receba no WhatsApp ótimos produtos de beleza, moda, calçados, bolsas, cabelos e skincare.",
        "Os preços mudam, os cupons acabam e as melhores ofertas podem durar pouco.",
        "Clique para entrar no grupo de WhatsApp",
        "ORIGINAIS",
        "CONFIÁVEIS",
        "aproximadamente entre 21h10 e 8h",
        "Só administradores enviam mensagens",
    ]
    assert all(copy in html for copy in required_copy)

    section_markers = [
        'class="hero"',
        'class="trust"',
        'class="section categories"',
        'id="como-funciona-titulo"',
        'id="ofertas-titulo"',
        'id="vitrine-titulo"',
        'id="urgencia-titulo"',
        'id="cta-final-titulo"',
        'class="footer"',
    ]
    positions = [html.index(marker) for marker in section_markers]
    assert positions == sorted(positions)


def test_landing_contains_exact_public_macro_groups() -> None:
    html = read(LANDING)
    for label in ("Beleza", "Moda", "Calçados", "Bolsas e acessórios", "Cabelos", "Skincare"):
        assert re.search(rf"<h3>{re.escape(label)}</h3>", html)


def test_landing_includes_minimum_seo_accessibility_and_responsive_contract() -> None:
    html = read(LANDING)
    css = read(PUBLIC_HTML / "assets" / "css" / "feminino.css")
    assert '<html lang="pt-BR">' in html
    assert '<meta name="viewport"' in html
    assert '<meta name="description"' in html
    assert "<title>" in html
    assert '<main id="conteudo">' in html
    assert 'class="skip-link"' in html
    assert 'alt="QR Code para acessar o grupo' in html
    assert ":focus-visible" in css
    assert "@media (min-width: 700px)" in css
    assert "@media (min-width: 960px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_whatsapp_ctas_use_only_the_controlled_route() -> None:
    html = read(LANDING)
    assert html.count('href="/go/whatsapp/feminino"') == 2
    assert html.count("Clique para entrar no grupo de WhatsApp") == 2
    assert "chat.whatsapp.com" not in html
    assert "chat.whatsapp.com" not in read(SCRIPT)


def test_landing_uses_local_brand_assets_and_three_real_offer_samples() -> None:
    html = read(LANDING)
    rendered_sources = html + read(PUBLIC_HTML / "assets" / "css" / "feminino.css")
    expected_assets = (
        "banner-elementos.png",
        "grupo-transparente.png",
        "oferta-1.jpg",
        "oferta-2.jpg",
        "oferta-3.jpg",
    )
    for filename in expected_assets:
        assert f"/assets/img/feminino/{filename}" in rendered_sources
        assert (PUBLIC_HTML / "assets" / "img" / "feminino" / filename).is_file()

    for offer_url in (
        "https://s.shopee.com.br/AAGgnIgSUT",
        "https://s.shopee.com.br/3LQMepDFhU",
        "https://s.shopee.com.br/8fRt16P5v5",
    ):
        assert offer_url in html
    assert 'data-placeholder="true"' not in html
    assert "Achados com carinho" not in html


def test_shopee_showcase_cta_uses_the_official_store_url() -> None:
    html = read(LANDING)
    assert 'href="https://collshp.com/ofertas_femininas"' in html
    assert "URL DA VITRINE PENDENTE" not in html
    assert 'aria-disabled="true"' not in html


def test_utm_script_has_an_explicit_allowlist_and_no_persistence() -> None:
    script = read(SCRIPT)
    for parameter in (
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
    ):
        assert f"'{parameter}'" in script
    assert "getAll(parameter)" in script
    assert "localStorage" not in script
    assert "document.cookie" not in script
    assert "sessionStorage" not in script


def test_redirect_uses_config_only_and_declares_temporary_redirect() -> None:
    php = read(REDIRECT)
    config = read(CONFIG)
    assert "WHATSAPP_GROUP_URL_FEMININO" in php
    assert "header('Location: ' . trim($destination), true, 302)" in php
    assert "FILTER_VALIDATE_URL" in php
    assert "WHATSAPP_INVITE_HOST" in php
    assert "$_GET" not in php
    assert "$_POST" not in php
    assert config.count("https://chat.whatsapp.com/") == 1
    assert re.search(r"https://chat\.whatsapp\.com/[A-Za-z0-9]{20,24}", config)


def test_clean_urls_are_internally_rewritten_without_directory_redirects() -> None:
    htaccess = read(PUBLIC_HTML / ".htaccess")
    assert "RewriteRule ^feminino/?$ feminino/index.html [END]" in htaccess
    assert (
        "RewriteRule ^go/whatsapp/feminino/?$ go/whatsapp/feminino/index.php [END]"
        in htaccess
    )


def test_invalid_config_path_is_controlled_and_has_no_redirect_fallback() -> None:
    php = read(REDIRECT)
    assert "http_response_code(503)" in php
    assert php.count("renderUnavailablePage();") >= 2
    assert "whatsapp-indisponivel.html" in php
    assert "301" not in php


def test_qr_is_local_and_encodes_only_the_controlled_route() -> None:
    html = read(LANDING)
    qr = PUBLIC_HTML / "assets" / "qr" / "whatsapp-feminino.png"
    assert '/assets/qr/whatsapp-feminino.png' in html
    assert qr.is_file()
    assert qr.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_no_forbidden_runtime_dependencies_or_tracking() -> None:
    production_text = "\n".join(
        read(path)
        for path in PUBLIC_HTML.rglob("*")
        if path.is_file() and path.suffix.lower() in {".html", ".css", ".js", ".php"}
    ).lower()
    for forbidden in ("node_modules", "supabase", "google-analytics", "gtag(", "fbq("):
        assert forbidden not in production_text

from ofertas_bot.product_resolver import ShopeePublicPageResolver, extract_shopee_product_ids

PUBLIC_HTML = """
<html><head>
<meta property="og:title" content="Produto teste">
<meta property="og:description" content="Descricao do produto">
<meta property="og:image" content="https://img.test/produto.jpg">
<meta property="og:video" content="https://video.test/produto.mp4">
<meta property="product:original_price:amount" content="100.00">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Produto teste",
"description":"Descricao do produto",
"image":["https://img.test/produto.jpg","https://img.test/produto-2.jpg"],
"offers":{"@type":"Offer","price":"80.00"},
"aggregateRating":{"ratingValue":"4.8","ratingCount":"1234"},
"seller":{"name":"Loja teste"}}
</script></head><body>{"historicalSold":321}</body></html>
"""


def test_extract_ids_from_standard_product_url() -> None:
    assert extract_shopee_product_ids(
        "https://shopee.com.br/Produto-qualquer-i.123.456?x=1"
    ) == (123, 456)


def test_ids_are_optional_for_short_affiliate_url() -> None:
    assert extract_shopee_product_ids("https://s.shopee.com.br/abc") == (None, None)


def test_resolver_uses_only_supplied_url_and_public_page() -> None:
    affiliate_url = "https://s.shopee.com.br/abc"
    resolved_url = "https://shopee.com.br/Produto-teste-i.123.456"
    requested: list[str] = []

    def page_fetcher(url: str) -> tuple[str, str]:
        requested.append(url)
        return resolved_url, PUBLIC_HTML

    product = ShopeePublicPageResolver(page_fetcher=page_fetcher).resolve(affiliate_url)

    assert requested == [affiliate_url]
    assert product.affiliate_url == affiliate_url
    assert product.resolved_url == resolved_url
    assert product.item_id == 456
    assert product.shop_id == 123
    assert product.title == "Produto teste"
    assert product.description == "Descricao do produto"
    assert product.price == 80
    assert product.old_price == 100
    assert product.discount_pct == 20
    assert product.rating == 4.8
    assert product.rating_count == 1234
    assert product.sales == 321
    assert product.shop_name == "Loja teste"
    assert product.images == (
        "https://img.test/produto.jpg",
        "https://img.test/produto-2.jpg",
    )
    assert product.videos == ("https://video.test/produto.mp4",)


def test_affiliate_url_is_never_replaced_by_resolved_url() -> None:
    product = ShopeePublicPageResolver(
        page_fetcher=lambda _: (
            "https://shopee.com.br/Produto-teste-i.123.456",
            PUBLIC_HTML,
        )
    ).resolve("https://s.shopee.com.br/minha-url-afiliada")
    assert product.to_offer().url == "https://s.shopee.com.br/minha-url-afiliada"

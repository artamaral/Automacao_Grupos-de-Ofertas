import csv
from pathlib import Path
from typing import Any

from ofertas_bot.tools.scrape_shopee_media import (
    extract_media_assets,
    scope_product_html,
    scrape_shopee_media,
)


def test_extract_media_assets_from_shopee_html_preserves_order() -> None:
    video_url = (
        r"https:\/\/down-aka-br.vod.susercontent.com\/api\/v4\/11110105\/mms\/"
        r"br-11110105-6kfks-m0yrlkzfm0lv7b.16000081728062864.mp4"
    )
    html = r'''
    <script>
    window.__DATA__ = {
      "video_info_list": [
        {
          "default_format": {
            "url": "__VIDEO_URL__"
          }
        }
      ],
      "image": "br-11134207-820m6-primary",
      "images": [
        "br-11134207-820m6-primary",
        "br-11134207-820m6-sizechart",
        "sg-11134201-7r98o-detail"
      ],
      "thumbnail": "https:\/\/cf.shopee.com.br\/file\/br-11134207-820m6-primary"
    }
    </script>
    '''.replace("__VIDEO_URL__", video_url)

    assets = extract_media_assets(html)

    assert [(asset.media_type, asset.media_url) for asset in assets] == [
        ("image", "https://cf.shopee.com.br/file/br-11134207-820m6-primary"),
        ("image", "https://cf.shopee.com.br/file/br-11134207-820m6-sizechart"),
        ("image", "https://cf.shopee.com.br/file/sg-11134201-7r98o-detail"),
        (
            "video",
            "https://down-aka-br.vod.susercontent.com/api/v4/11110105/mms/"
            "br-11110105-6kfks-m0yrlkzfm0lv7b.16000081728062864.mp4",
        ),
    ]
    assert [asset.position for asset in assets] == [1, 2, 3, 4]


def test_scrape_shopee_media_writes_csv_without_validation(tmp_path: Path) -> None:
    output_path = tmp_path / "media.csv"
    html = b'''
    <script>
    {"images":["br-11134207-820m6-primary","br-11134207-820m6-secondary"],
    "video":"https://down-aka-br.vod.susercontent.com/api/v4/11110105/mms/item.mp4"}
    </script>
    '''
    opener = FakeOpener({("GET", "https://shopee.com.br/product/296735539/7282718770"): html})

    result = scrape_shopee_media(
        source_url="https://shopee.com.br/product/296735539/7282718770",
        output_path=output_path,
        validate=False,
        opener=opener,
    )

    rows = list(csv.DictReader(output_path.open(encoding="utf-8")))
    assert result.shop_id == "296735539"
    assert result.item_id == "7282718770"
    assert [row["media_type"] for row in rows] == ["image", "image", "video"]
    assert rows[0]["media_url"] == "https://cf.shopee.com.br/file/br-11134207-820m6-primary"
    assert rows[0]["status"] == "not_validated"
    assert rows[2]["media_url"] == (
        "https://down-aka-br.vod.susercontent.com/api/v4/11110105/mms/item.mp4"
    )


def test_extract_media_assets_scopes_to_product_card_inside_main_container() -> None:
    html = r'''
    <div>
      <script>{"images":["br-11134207-outside-page"]}</script>
    </div>
    <div role="main" class="container">
      <div class="recommendations">
        <script>{"images":["br-11134207-outside-card"]}</script>
      </div>
      <div class="flex card vr0998">
        <script>
          {"images":["br-11134207-product-1","br-11134207-product-2"]}
        </script>
      </div>
      <video class="QODm2C exqDJH" src="https://down-aka-br.vod.susercontent.com/api/v4/11110105/mms/product.mp4"></video>
    </div>
    '''

    scoped_html = scope_product_html(html)
    assets = extract_media_assets(html)

    assert "outside-page" not in scoped_html
    assert "outside-card" not in scoped_html
    assert [(asset.media_type, asset.media_url) for asset in assets] == [
        ("image", "https://cf.shopee.com.br/file/br-11134207-product-1"),
        ("image", "https://cf.shopee.com.br/file/br-11134207-product-2"),
        (
            "video",
            "https://down-aka-br.vod.susercontent.com/api/v4/11110105/mms/product.mp4",
        ),
    ]


def test_extract_media_assets_includes_product_json_video_info_list() -> None:
    html = r'''
    <script>
    {"itemid":7282718770,"shopid":296735539,
     "images":["br-11134207-json-extra"],
     "video_info_list":[
       {"video_id":"api/v4/11110105/mms/product.mp4",
        "formats":[
          {"url":"https://down-bs-br.vod.susercontent.com/api/v4/11110105/mms/product.16000081708099433.mp4"},
          {"url":"https://mms.vod.susercontent.com/api/v4/11110105/mms/product.default.mp4"}
        ]}
     ]}
    </script>
    <div role="main" class="container">
      <div class="flex card vr0998">
        <script>{"images":["br-11134207-product-1"]}</script>
      </div>
    </div>
    '''

    assets = extract_media_assets(html, item_id="7282718770", shop_id="296735539")

    assert [(asset.media_type, asset.media_url) for asset in assets] == [
        ("image", "https://cf.shopee.com.br/file/br-11134207-product-1"),
        (
            "video",
            "https://down-bs-br.vod.susercontent.com/api/v4/11110105/mms/"
            "product.16000081708099433.mp4",
        ),
    ]


def test_extract_media_assets_prefers_product_gallery_images_without_rendered_card() -> None:
    html = r'''
    <script>
    {"itemid":7282718770,"shopid":296735539,
     "tier_variations":[
       {"images":["br-11134207-variation-1","br-11134207-variation-2","br-11134207-variation-3"]}
     ],
     "liked_count":null,
     "images":[
       "br-11134207-product-1",
       "br-11134207-product-2",
       "br-11134207-product-3",
       "br-11134207-product-4",
       "br-11134207-product-5",
       "br-11134207-product-6",
       "br-11134207-product-7",
       "br-11134207-product-8",
       "br-11134207-product-9"
     ],
     "video_info_list":[
       {"url":"https://down-bs-br.vod.susercontent.com/api/v4/11110105/mms/product.mp4"}
     ]}
    </script>
    '''

    assets = extract_media_assets(html, item_id="7282718770", shop_id="296735539")

    assert [asset.media_type for asset in assets] == ["image"] * 9 + ["video"]
    assert assets[0].media_url == "https://cf.shopee.com.br/file/br-11134207-product-1"
    assert assets[8].media_url == "https://cf.shopee.com.br/file/br-11134207-product-9"
    assert all("variation" not in asset.media_url for asset in assets)


def test_extract_media_assets_prefers_long_images_when_variant_images_are_larger() -> None:
    html = r'''
    <script>
    {"itemid":48711462311,"shopid":1296459836,
     "images":[
       "br-11134207-variant-1",
       "br-11134207-variant-2",
       "br-11134207-variant-3",
       "br-11134207-variant-4",
       "br-11134207-variant-5",
       "br-11134207-variant-6"
     ],
     "long_images":[
       "br-11134207-detail-1",
       "br-11134207-detail-2",
       "br-11134207-detail-3",
       "br-11134207-detail-4",
       "br-11134207-detail-5"
     ],
     "video_info_list":[
       {"url":"https://down-bs-br.vod.susercontent.com/api/v4/11110105/mms/product.mp4"}
     ]}
    </script>
    '''

    assets = extract_media_assets(html, item_id="48711462311", shop_id="1296459836")

    assert [asset.media_type for asset in assets] == ["image"] * 5 + ["video"]
    assert assets[0].media_url == "https://cf.shopee.com.br/file/br-11134207-detail-1"
    assert all("variant" not in asset.media_url for asset in assets)


def test_extract_media_assets_prefers_long_images_over_single_main_image() -> None:
    html = r'''
    <script>
    {"itemid":58256738919,"shopid":1651898003,
     "tier_variations":[
       {"images":[
         "br-11134207-variant-1",
         "br-11134207-variant-2",
         "br-11134207-variant-3",
         "br-11134207-variant-4"
       ]}
     ],
     "liked_count":null,
     "images":["br-11134207-main-image"],
     "long_images":[
       "br-11134207-detail-1",
       "br-11134207-detail-2",
       "br-11134207-detail-3",
       "br-11134207-detail-4",
       "br-11134207-detail-5",
       "br-11134207-detail-6"
     ],
     "video_info_list":[]}
    </script>
    '''

    assets = extract_media_assets(html, item_id="58256738919", shop_id="1651898003")

    assert [asset.media_type for asset in assets] == ["image"] * 6
    assert assets[0].media_url == "https://cf.shopee.com.br/file/br-11134207-detail-1"
    assert assets[5].media_url == "https://cf.shopee.com.br/file/br-11134207-detail-6"
    assert all("main-image" not in asset.media_url for asset in assets)


def test_scrape_shopee_media_validates_with_range_request(tmp_path: Path) -> None:
    output_path = tmp_path / "media.csv"
    page_url = "https://shopee.com.br/product/1/2"
    image_url = "https://cf.shopee.com.br/file/br-11134207-820m6-primary"
    opener = FakeOpener(
        {
            ("GET", page_url): b'{"images":["br-11134207-820m6-primary"]}',
            ("GET", image_url): b"x",
        },
        headers={
            image_url: {"Content-Type": "image/jpeg", "Content-Length": "123"},
        },
    )

    scrape_shopee_media(
        source_url=page_url,
        output_path=output_path,
        validate=True,
        opener=opener,
    )

    rows = list(csv.DictReader(output_path.open(encoding="utf-8")))
    assert rows[0]["status"] == "valid"
    assert rows[0]["http_status"] == "200"
    assert rows[0]["content_type"] == "image/jpeg"


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body
        self.status = status
        self.headers = headers or {}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self, *_: object) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status


class FakeOpener:
    def __init__(
        self,
        responses: dict[tuple[str, str], bytes],
        *,
        headers: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self.responses = responses
        self.headers = headers or {}
        self.requests: list[Any] = []

    def __call__(self, request: Any, *, timeout: float) -> FakeResponse:
        del timeout
        self.requests.append(request)
        method = request.get_method()
        url = request.full_url
        return FakeResponse(self.responses[(method, url)], headers=self.headers.get(url))

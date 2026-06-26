from __future__ import annotations

from facebook_auto_post.notion_client import NotionConfig, NotionPropertyClient
from facebook_auto_post.property_models import PropertyListing


SCHEMA = {
    "物件名": {"type": "title"},
    "外部ID": {"type": "rich_text"},
    "コミュニティ": {"type": "rich_text"},
    "投稿URL": {"type": "url"},
    "家賃": {"type": "number"},
    "間取り": {"type": "rich_text"},
    "タグ": {"type": "multi_select"},
    "信頼度": {"type": "number"},
}


def make_listing() -> PropertyListing:
    return PropertyListing(
        external_id="property-abc",
        title="新宿駅 / 1LDK / 12万円",
        source_name="コミュニティA",
        source_post_id="fb-1",
        body="新宿駅 徒歩7分 1LDK 家賃12万円",
        post_url="https://example.com/post/1",
        rent_yen=120000,
        layout="1LDK",
        tags=["ペット可"],
        confidence=0.9,
    )


def test_build_page_properties_matches_available_schema():
    client = NotionPropertyClient(
        NotionConfig(api_key="secret", data_source_id="data-source-id"),
        session=object(),
    )

    properties = client.build_page_properties(make_listing(), SCHEMA)

    assert properties["物件名"]["title"][0]["text"]["content"].startswith("新宿駅")
    assert properties["外部ID"]["rich_text"][0]["text"]["content"] == "property-abc"
    assert properties["家賃"]["number"] == 120000.0
    assert properties["タグ"]["multi_select"] == [{"name": "ペット可"}]


class FakeResponse:
    def __init__(self, payload: dict, *, ok: bool = True, status_code: int = 200) -> None:
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self) -> None:
        self.calls = []

    def get(self, url, *, headers, timeout):
        self.calls.append(("GET", url, None))
        return FakeResponse({"properties": SCHEMA})

    def post(self, url, *, headers, json, timeout):
        self.calls.append(("POST", url, json))
        if url.endswith("/query"):
            return FakeResponse({"results": []})
        return FakeResponse({"id": "new-page"})


def test_upsert_listing_queries_duplicate_then_creates():
    session = FakeSession()
    client = NotionPropertyClient(
        NotionConfig(api_key="secret", data_source_id="data-source-id"),
        session=session,
    )

    status, result = client.upsert_listing(make_listing())

    assert status == "created"
    assert result == {"id": "new-page"}
    assert session.calls[0][0] == "GET"
    assert session.calls[1][1].endswith("/v1/data_sources/data-source-id/query")
    assert session.calls[2][1].endswith("/v1/pages")

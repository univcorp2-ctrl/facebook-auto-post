from __future__ import annotations

import pytest

from facebook_auto_post.client import FacebookAPIError, FacebookPageClient


class FakeResponse:
    def __init__(self, *, ok: bool, payload: dict, status_code: int = 200, text: str = "") -> None:
        self.ok = ok
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls = []

    def post(self, url, data, timeout):
        self.calls.append({"url": url, "data": data, "timeout": timeout})
        return self.response


def test_publish_feed_post_sends_expected_payload():
    session = FakeSession(FakeResponse(ok=True, payload={"id": "page_123"}))
    client = FacebookPageClient(graph_version="v25.0", session=session, timeout=7)

    result = client.publish_feed_post(
        page_id=" page-id ",
        page_access_token=" token ",
        message=" hello ",
        link=" https://example.com ",
    )

    assert result == {"id": "page_123"}
    assert session.calls == [
        {
            "url": "https://graph.facebook.com/v25.0/page-id/feed",
            "data": {
                "access_token": "token",
                "published": "true",
                "message": "hello",
                "link": "https://example.com",
            },
            "timeout": 7,
        }
    ]


def test_publish_feed_post_requires_content():
    client = FacebookPageClient(session=FakeSession(FakeResponse(ok=True, payload={})))

    with pytest.raises(ValueError, match="message or link is required"):
        client.publish_feed_post(page_id="page-id", page_access_token="token")


def test_publish_feed_post_raises_api_error():
    session = FakeSession(
        FakeResponse(
            ok=False,
            status_code=400,
            payload={"error": {"message": "Invalid OAuth access token", "code": 190}},
        )
    )
    client = FacebookPageClient(session=session)

    with pytest.raises(FacebookAPIError, match="code=190"):
        client.publish_feed_post(page_id="page-id", page_access_token="bad-token", message="hello")

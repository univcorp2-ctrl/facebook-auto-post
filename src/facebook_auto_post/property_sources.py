from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

import requests

from .property_models import CommunityPost


class SourceError(RuntimeError):
    """Raised when a source cannot be loaded or normalized."""


class ReadHTTPSession(Protocol):
    def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any],
        timeout: int,
    ) -> Any: ...


MESSAGE_KEYS = ("message", "text", "body", "content", "本文", "投稿本文")
SOURCE_ID_KEYS = ("source_id", "id", "post_id", "投稿ID")
SOURCE_NAME_KEYS = ("source_name", "group", "group_name", "community", "コミュニティ")
AUTHOR_KEYS = ("author", "from", "user", "投稿者")
CREATED_KEYS = ("created_time", "posted_at", "date", "日時", "投稿日")
URL_KEYS = ("permalink_url", "url", "link", "投稿URL")


def _first_string(raw: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _fallback_id(raw: Mapping[str, Any], *, index: int) -> str:
    payload = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"row-{index}-{digest}"


def _normalise_post(raw: Mapping[str, Any], *, index: int) -> CommunityPost:
    message = _first_string(raw, MESSAGE_KEYS)
    if not message:
        raise SourceError(f"row {index}: message/text/body column is required")
    source_id = _first_string(raw, SOURCE_ID_KEYS) or _fallback_id(raw, index=index)
    source_name = _first_string(raw, SOURCE_NAME_KEYS) or "community"
    author = _first_string(raw, AUTHOR_KEYS)
    created_time = _first_string(raw, CREATED_KEYS)
    permalink_url = _first_string(raw, URL_KEYS)
    return CommunityPost(
        source_id=source_id,
        source_name=source_name,
        message=message,
        author=author,
        created_time=created_time,
        permalink_url=permalink_url,
        raw=dict(raw),
    )


def load_posts_from_csv(path: str | Path) -> list[CommunityPost]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SourceError("CSV must include a header row")
        return [_normalise_post(row, index=index) for index, row in enumerate(reader, start=1)]


def load_posts_from_json(path: str | Path) -> list[CommunityPost]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("posts") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise SourceError("JSON source must be a list or an object with a posts list")
    normalized: list[CommunityPost] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise SourceError(f"row {index}: each JSON post must be an object")
        normalized.append(_normalise_post(row, index=index))
    return normalized


def load_posts_from_file(path: str | Path, *, source_type: str = "auto") -> list[CommunityPost]:
    source_path = Path(path)
    clean_type = source_type.lower().strip()
    if clean_type == "auto":
        clean_type = source_path.suffix.lower().lstrip(".")
    if clean_type == "csv":
        return load_posts_from_csv(source_path)
    if clean_type == "json":
        return load_posts_from_json(source_path)
    raise SourceError(f"Unsupported source type: {source_type}")


@dataclass
class FacebookGroupFeedSource:
    """Best-effort Graph API source for environments with explicit approved access.

    Meta removed broad third-party Facebook Groups API access in 2024. This class does not
    scrape Facebook pages. It only calls Graph API endpoints when the caller already has a
    valid token, group IDs, and permission to process the data.
    """

    group_ids: list[str]
    access_token: str
    graph_version: str = "v25.0"
    limit: int = 25
    session: ReadHTTPSession | None = None
    timeout: int = 20
    base_url: str = "https://graph.facebook.com"

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

    def load(self) -> list[CommunityPost]:
        if not self.group_ids:
            raise SourceError("FACEBOOK_GROUP_IDS is required for facebook-graph source")
        if not self.access_token.strip():
            raise SourceError("FB_USER_ACCESS_TOKEN is required for facebook-graph source")

        posts: list[CommunityPost] = []
        version = self.graph_version.strip().strip("/")
        assert self.session is not None
        for group_id in self.group_ids:
            url = f"{self.base_url.rstrip('/')}/{version}/{group_id}/feed"
            response = self.session.get(
                url,
                params={
                    "access_token": self.access_token,
                    "fields": "id,message,created_time,permalink_url,from{name}",
                    "limit": self.limit,
                },
                timeout=self.timeout,
            )
            payload = self._response_json(response)
            if not getattr(response, "ok", False):
                raise SourceError(self._error_message(response, payload, group_id=group_id))
            rows = payload.get("data", []) if isinstance(payload, dict) else []
            for row in rows:
                if not isinstance(row, dict) or not row.get("message"):
                    continue
                author = row.get("from", {}).get("name") if isinstance(row.get("from"), dict) else None
                posts.append(
                    CommunityPost(
                        source_id=str(row.get("id")),
                        source_name=f"Facebook Group {group_id}",
                        message=str(row.get("message")),
                        author=author,
                        created_time=row.get("created_time") if isinstance(row.get("created_time"), str) else None,
                        permalink_url=(
                            row.get("permalink_url") if isinstance(row.get("permalink_url"), str) else None
                        ),
                        raw=row,
                    )
                )
        return posts

    @staticmethod
    def _response_json(response: Any) -> Any:
        try:
            return response.json()
        except ValueError:
            return None

    @staticmethod
    def _error_message(response: Any, payload: Any, *, group_id: str) -> str:
        status = getattr(response, "status_code", "unknown")
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        message = error.get("message") or getattr(response, "text", "Unknown Facebook Graph API error")
        return f"Failed to load group {group_id}: status={status} {message}"

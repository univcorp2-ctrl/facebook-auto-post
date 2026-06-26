from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PostContent:
    message: str
    link: str | None = None

    def as_payload(self) -> dict[str, str]:
        payload = {"message": self.message}
        if self.link:
            payload["link"] = self.link
        return payload


def _normalise_post(raw: Any, *, index: int) -> PostContent:
    if not isinstance(raw, dict):
        raise ValueError(f"posts[{index}] must be an object")
    message = raw.get("message")
    link = raw.get("link")
    if not isinstance(message, str) or not message.strip():
        raise ValueError(f"posts[{index}].message must be a non-empty string")
    if link is not None and (not isinstance(link, str) or not link.strip()):
        raise ValueError(f"posts[{index}].link must be a non-empty string when provided")
    return PostContent(message=message.strip(), link=link.strip() if isinstance(link, str) else None)


def load_posts(path: str | Path) -> list[PostContent]:
    posts_path = Path(path)
    data = json.loads(posts_path.read_text(encoding="utf-8"))
    raw_posts = data.get("posts") if isinstance(data, dict) else data
    if not isinstance(raw_posts, list) or not raw_posts:
        raise ValueError("posts file must contain a non-empty list or an object with a non-empty posts list")
    return [_normalise_post(raw_post, index=index) for index, raw_post in enumerate(raw_posts)]


def select_post(
    posts: list[PostContent],
    *,
    today: date | None = None,
    index: int | None = None,
) -> PostContent:
    if not posts:
        raise ValueError("posts must not be empty")
    if index is not None:
        return posts[index % len(posts)]
    current_date = today or date.today()
    return posts[current_date.toordinal() % len(posts)]


def resolve_post_content(
    *,
    post_text: str | None,
    post_link: str | None,
    posts_file: str | Path,
    post_index: int | None = None,
    today: date | None = None,
) -> PostContent:
    if post_text and post_text.strip():
        clean_link = post_link.strip() if isinstance(post_link, str) and post_link.strip() else None
        return PostContent(message=post_text.strip(), link=clean_link)
    posts = load_posts(posts_file)
    return select_post(posts, today=today, index=post_index)

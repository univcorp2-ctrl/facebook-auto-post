from __future__ import annotations

from dataclasses import dataclass
import os


def parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class AppConfig:
    page_id: str | None
    page_access_token: str | None
    graph_version: str
    posts_file: str
    dry_run: bool
    post_text: str | None
    post_link: str | None
    post_index: int | None

    @classmethod
    def from_env(cls) -> "AppConfig":
        raw_index = os.getenv("POST_INDEX")
        post_index = int(raw_index) if raw_index not in (None, "") else None
        return cls(
            page_id=os.getenv("FB_PAGE_ID"),
            page_access_token=os.getenv("FB_PAGE_ACCESS_TOKEN"),
            graph_version=os.getenv("FB_GRAPH_VERSION", "v25.0"),
            posts_file=os.getenv("POSTS_FILE", "posts/posts.json"),
            dry_run=parse_bool(os.getenv("DRY_RUN"), default=False),
            post_text=os.getenv("POST_TEXT"),
            post_link=os.getenv("POST_LINK"),
            post_index=post_index,
        )

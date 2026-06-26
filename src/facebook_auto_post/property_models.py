from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommunityPost:
    """A normalized post from a community, file export, or approved API source."""

    source_id: str
    source_name: str
    message: str
    author: str | None = None
    created_time: str | None = None
    permalink_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PropertyListing:
    """Structured property listing extracted from a community post."""

    external_id: str
    title: str
    source_name: str
    source_post_id: str
    body: str
    author: str | None = None
    posted_at: str | None = None
    post_url: str | None = None
    rent_yen: int | None = None
    layout: str | None = None
    station: str | None = None
    walk_minutes: int | None = None
    area_sqm: float | None = None
    address: str | None = None
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

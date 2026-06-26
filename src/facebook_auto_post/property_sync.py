from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .notion_client import NotionPropertyClient
from .property_models import CommunityPost, PropertyListing
from .property_parser import extract_property_listing


@dataclass(frozen=True)
class SyncOptions:
    dry_run: bool = True
    min_confidence: float = 0.35
    include_low_confidence: bool = False


@dataclass
class SyncReport:
    source_count: int = 0
    parsed_count: int = 0
    skipped_low_confidence_count: int = 0
    source_duplicate_count: int = 0
    notion_duplicate_count: int = 0
    created_count: int = 0
    dry_run: bool = True
    errors: list[str] = field(default_factory=list)
    listings: list[PropertyListing] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_count": self.source_count,
            "parsed_count": self.parsed_count,
            "skipped_low_confidence_count": self.skipped_low_confidence_count,
            "source_duplicate_count": self.source_duplicate_count,
            "notion_duplicate_count": self.notion_duplicate_count,
            "created_count": self.created_count,
            "dry_run": self.dry_run,
            "errors": self.errors,
            "listings": [listing.as_dict() for listing in self.listings],
        }


class PropertySyncer:
    def __init__(
        self,
        *,
        notion_client: NotionPropertyClient | None = None,
        options: SyncOptions | None = None,
    ) -> None:
        self.notion_client = notion_client
        self.options = options or SyncOptions()

    def run(self, posts: list[CommunityPost]) -> SyncReport:
        report = SyncReport(source_count=len(posts), dry_run=self.options.dry_run)
        seen_external_ids: set[str] = set()
        schema = self.notion_client.retrieve_schema() if self.notion_client and not self.options.dry_run else None

        for post in posts:
            try:
                listing = extract_property_listing(post)
                if (
                    listing.confidence < self.options.min_confidence
                    and not self.options.include_low_confidence
                ):
                    report.skipped_low_confidence_count += 1
                    continue
                if listing.external_id in seen_external_ids:
                    report.source_duplicate_count += 1
                    continue
                seen_external_ids.add(listing.external_id)
                report.parsed_count += 1
                report.listings.append(listing)

                if self.options.dry_run or self.notion_client is None:
                    continue

                status, _ = self.notion_client.upsert_listing(listing, schema=schema)
                if status == "duplicate":
                    report.notion_duplicate_count += 1
                elif status == "created":
                    report.created_count += 1
            except Exception as exc:  # noqa: BLE001 - collect per-row errors for batch jobs.
                report.errors.append(f"{post.source_id}: {exc}")
        return report

from __future__ import annotations

from facebook_auto_post.property_models import CommunityPost
from facebook_auto_post.property_sync import PropertySyncer, SyncOptions


def test_property_syncer_dry_run_filters_and_dedupes():
    posts = [
        CommunityPost(
            source_id="1",
            source_name="A",
            message="渋谷駅 徒歩5分 1K 家賃8万円 22㎡",
            permalink_url="https://example.com/p/1",
        ),
        CommunityPost(
            source_id="2",
            source_name="A",
            message="渋谷駅 徒歩5分 1K 家賃8万円 22㎡",
            permalink_url="https://example.com/p/1",
        ),
        CommunityPost(source_id="3", source_name="A", message="ランチ会のお知らせ"),
    ]

    report = PropertySyncer(options=SyncOptions(dry_run=True, min_confidence=0.35)).run(posts)

    assert report.source_count == 3
    assert report.parsed_count == 1
    assert report.source_duplicate_count == 1
    assert report.skipped_low_confidence_count == 1
    assert report.listings[0].rent_yen == 80000

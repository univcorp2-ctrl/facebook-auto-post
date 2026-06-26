from __future__ import annotations

from facebook_auto_post.property_models import CommunityPost
from facebook_auto_post.property_parser import extract_property_listing


def test_extract_property_listing_from_japanese_post():
    post = CommunityPost(
        source_id="fb-001",
        source_name="東京賃貸コミュニティ",
        author="山田",
        created_time="2026-06-25T10:15:00+09:00",
        permalink_url="https://facebook.com/groups/example/posts/1",
        message=(
            "新宿駅 徒歩7分 1LDK 家賃12.5万円 35.2㎡\n"
            "東京都新宿区西新宿 ペット可 即入居 バストイレ別"
        ),
    )

    listing = extract_property_listing(post)

    assert listing.rent_yen == 125000
    assert listing.layout == "1LDK"
    assert listing.station == "新宿駅"
    assert listing.walk_minutes == 7
    assert listing.area_sqm == 35.2
    assert listing.address.startswith("東京都新宿区")
    assert "ペット可" in listing.tags
    assert listing.confidence >= 0.8
    assert listing.external_id.startswith("property-")


def test_extract_property_listing_handles_low_confidence_text():
    post = CommunityPost(source_id="1", source_name="雑談", message="今日はランチ会です")

    listing = extract_property_listing(post)

    assert listing.confidence == 0.0
    assert listing.title == "今日はランチ会です"

from __future__ import annotations

import hashlib
import re
import unicodedata

from .property_models import CommunityPost, PropertyListing

PROPERTY_KEYWORDS = (
    "物件",
    "部屋",
    "賃貸",
    "家賃",
    "賃料",
    "月額",
    "敷金",
    "礼金",
    "間取り",
    "入居",
    "マンション",
    "アパート",
    "戸建",
    "駅",
    "徒歩",
    "㎡",
    "平米",
)

TAG_KEYWORDS = (
    "ペット可",
    "ペット相談",
    "敷金礼金なし",
    "敷金なし",
    "礼金なし",
    "仲介手数料なし",
    "初期費用",
    "即入居",
    "家具家電付き",
    "バストイレ別",
    "オートロック",
    "駐車場",
    "外国籍可",
    "女性限定",
    "事務所可",
    "ルームシェア可",
)

RENT_PATTERNS = (
    re.compile(r"(?:家賃|賃料|月額|月々|月)\s*[:：]?\s*(?:¥|￥)?\s*([0-9０-９,.]+)\s*(万)?\s*円?", re.I),
    re.compile(r"(?:¥|￥)\s*([0-9０-９,]+)"),
    re.compile(r"([0-9０-９]+(?:\.[0-9０-９]+)?)\s*万円"),
)
LAYOUT_RE = re.compile(r"(?:[1-9][0-9]?\s*(?:SLDK|LDK|DK|K|R)|ワンルーム)", re.I)
STATION_RE = re.compile(
    r"(?P<station>[一-龯ぁ-んァ-ンA-Za-z0-9０-９ヶケー・\s]{1,24}駅)\s*"
    r"(?:徒歩|歩いて|歩)\s*(?P<minutes>[0-9０-９]+)\s*分"
)
AREA_RE = re.compile(r"([0-9０-９]+(?:\.[0-9０-９]+)?)\s*(?:㎡|m2|m²|平米)", re.I)
ADDRESS_RE = re.compile(r"(東京都|北海道|(?:京都|大阪)府|.{2,3}県).{2,80}")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", normalized).strip()


def parse_amount_to_yen(raw: str, *, has_man_unit: bool) -> int | None:
    cleaned = unicodedata.normalize("NFKC", raw).replace(",", "").strip()
    if not cleaned:
        return None
    try:
        amount = float(cleaned)
    except ValueError:
        return None
    if has_man_unit:
        return int(round(amount * 10000))
    return int(round(amount))


def extract_rent_yen(text: str) -> int | None:
    for pattern in RENT_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        has_man = "万" in match.group(0)
        rent = parse_amount_to_yen(match.group(1), has_man_unit=has_man)
        if rent is None:
            continue
        if not has_man and rent < 1000 and re.search(r"家賃|賃料|月額|月々", match.group(0)):
            rent *= 10000
        if 10_000 <= rent <= 5_000_000:
            return rent
    return None


def extract_layout(text: str) -> str | None:
    match = LAYOUT_RE.search(text)
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(0).upper()).replace("ワンルーム", "1R")


def extract_station_and_walk(text: str) -> tuple[str | None, int | None]:
    match = STATION_RE.search(text)
    if not match:
        return None, None
    station = re.sub(r"\s+", "", match.group("station"))
    minutes = int(unicodedata.normalize("NFKC", match.group("minutes")))
    return station, minutes


def extract_area_sqm(text: str) -> float | None:
    match = AREA_RE.search(text)
    if not match:
        return None
    value = unicodedata.normalize("NFKC", match.group(1))
    try:
        return float(value)
    except ValueError:
        return None


def extract_address(text: str) -> str | None:
    for line in text.splitlines():
        clean_line = line.strip(" -　")
        if not clean_line:
            continue
        match = ADDRESS_RE.search(clean_line)
        if match:
            return match.group(0)[:120]
    compact = re.sub(r"\s+", " ", text)
    match = ADDRESS_RE.search(compact)
    return match.group(0)[:120] if match else None


def extract_tags(text: str) -> list[str]:
    return [keyword for keyword in TAG_KEYWORDS if keyword in text]


def build_external_id(post: CommunityPost) -> str:
    stable_source = post.permalink_url or f"{post.source_name}:{post.source_id}:{post.message}"
    digest = hashlib.sha256(stable_source.encode("utf-8")).hexdigest()[:20]
    return f"property-{digest}"


def build_title(
    *,
    text: str,
    rent_yen: int | None,
    layout: str | None,
    station: str | None,
    address: str | None,
) -> str:
    parts: list[str] = []
    if station:
        parts.append(station)
    elif address:
        parts.append(address[:24])
    if layout:
        parts.append(layout)
    if rent_yen:
        rent_text = f"{rent_yen / 10000:g}万円"
        parts.append(rent_text)
    if parts:
        return " / ".join(dict.fromkeys(parts))[:120]

    for line in text.splitlines():
        clean_line = line.strip(" ・-—　")
        if clean_line:
            return clean_line[:120]
    return "物件情報"


def score_listing(
    *,
    text: str,
    rent_yen: int | None,
    layout: str | None,
    station: str | None,
    area_sqm: float | None,
    address: str | None,
    tags: list[str],
) -> float:
    score = 0.0
    score += 0.28 if rent_yen else 0.0
    score += 0.18 if layout else 0.0
    score += 0.18 if station else 0.0
    score += 0.10 if area_sqm else 0.0
    score += 0.10 if address else 0.0
    score += min(len(tags), 3) * 0.03
    score += 0.10 if any(keyword in text for keyword in PROPERTY_KEYWORDS) else 0.0
    return round(min(score, 1.0), 2)


def extract_property_listing(post: CommunityPost) -> PropertyListing:
    text = normalize_text(post.message)
    rent_yen = extract_rent_yen(text)
    layout = extract_layout(text)
    station, walk_minutes = extract_station_and_walk(text)
    area_sqm = extract_area_sqm(text)
    address = extract_address(text)
    tags = extract_tags(text)
    confidence = score_listing(
        text=text,
        rent_yen=rent_yen,
        layout=layout,
        station=station,
        area_sqm=area_sqm,
        address=address,
        tags=tags,
    )
    title = build_title(
        text=text,
        rent_yen=rent_yen,
        layout=layout,
        station=station,
        address=address,
    )
    return PropertyListing(
        external_id=build_external_id(post),
        title=title,
        source_name=post.source_name,
        source_post_id=post.source_id,
        body=text,
        author=post.author,
        posted_at=post.created_time,
        post_url=post.permalink_url,
        rent_yen=rent_yen,
        layout=layout,
        station=station,
        walk_minutes=walk_minutes,
        area_sqm=area_sqm,
        address=address,
        tags=tags,
        confidence=confidence,
    )

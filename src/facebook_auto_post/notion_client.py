from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Mapping, Protocol

import requests

from .property_models import PropertyListing

Schema = Mapping[str, Mapping[str, Any]]


class NotionAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, response: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class NotionHTTPSession(Protocol):
    def get(self, url: str, *, headers: Mapping[str, str], timeout: int) -> Any: ...

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: int,
    ) -> Any: ...


@dataclass(frozen=True)
class NotionConfig:
    api_key: str
    data_source_id: str | None = None
    database_id: str | None = None
    notion_version: str = "2026-03-11"
    base_url: str = "https://api.notion.com"
    timeout: int = 20

    @classmethod
    def from_env(cls) -> "NotionConfig":
        return cls(
            api_key=os.getenv("NOTION_API_KEY", ""),
            data_source_id=os.getenv("NOTION_DATA_SOURCE_ID"),
            database_id=os.getenv("NOTION_DATABASE_ID"),
            notion_version=os.getenv("NOTION_VERSION", "2026-03-11"),
        )

    def validate(self) -> None:
        if not self.api_key.strip():
            raise ValueError("NOTION_API_KEY is required")
        if not self.data_source_id and not self.database_id:
            raise ValueError("NOTION_DATA_SOURCE_ID is required, or NOTION_DATABASE_ID for legacy mode")

    @property
    def uses_data_source(self) -> bool:
        return bool(self.data_source_id)

    @property
    def parent_id(self) -> str:
        if self.data_source_id:
            return self.data_source_id
        if self.database_id:
            return self.database_id
        raise ValueError("Notion parent ID is not configured")


PROPERTY_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("物件名", "Name", "Title", "タイトル"),
    "external_id": ("外部ID", "External ID", "external_id", "Source ID"),
    "source": ("コミュニティ", "Source", "出典", "source_name"),
    "author": ("投稿者", "Author", "author"),
    "posted_at": ("投稿日", "Posted At", "posted_at"),
    "url": ("投稿URL", "URL", "Post URL", "permalink_url"),
    "rent": ("家賃", "Rent", "rent_yen"),
    "layout": ("間取り", "Layout", "layout"),
    "station": ("最寄駅", "Station", "station"),
    "walk": ("徒歩分", "Walk Minutes", "walk_minutes"),
    "area": ("面積㎡", "Area sqm", "area_sqm"),
    "address": ("住所", "Address", "address"),
    "tags": ("タグ", "Tags", "tags"),
    "body": ("本文", "Body", "Message", "body"),
    "confidence": ("信頼度", "Confidence", "confidence"),
}


class NotionPropertyClient:
    def __init__(self, config: NotionConfig, session: NotionHTTPSession | None = None) -> None:
        config.validate()
        self.config = config
        self.session = session or requests.Session()

    def retrieve_schema(self) -> dict[str, Mapping[str, Any]]:
        endpoint = (
            f"/v1/data_sources/{self.config.parent_id}"
            if self.config.uses_data_source
            else f"/v1/databases/{self.config.parent_id}"
        )
        data = self._get(endpoint)
        properties = data.get("properties", {}) if isinstance(data, dict) else {}
        if not isinstance(properties, dict):
            raise NotionAPIError("Notion schema response did not include properties")
        return properties

    def upsert_listing(
        self,
        listing: PropertyListing,
        *,
        schema: Schema | None = None,
    ) -> tuple[str, dict[str, Any]]:
        active_schema = schema or self.retrieve_schema()
        if self.find_existing(listing.external_id, schema=active_schema):
            return "duplicate", {}
        created = self.create_listing(listing, schema=active_schema)
        return "created", created

    def find_existing(self, external_id: str, *, schema: Schema | None = None) -> bool:
        active_schema = schema or self.retrieve_schema()
        match = self._find_property(active_schema, "external_id", allowed_types={"rich_text", "title"})
        if match is None:
            return False
        property_name, property_type = match
        filter_type = "title" if property_type == "title" else "rich_text"
        endpoint = (
            f"/v1/data_sources/{self.config.parent_id}/query"
            if self.config.uses_data_source
            else f"/v1/databases/{self.config.parent_id}/query"
        )
        result = self._post(
            endpoint,
            {
                "filter": {"property": property_name, filter_type: {"equals": external_id}},
                "page_size": 1,
            },
        )
        rows = result.get("results", []) if isinstance(result, dict) else []
        return bool(rows)

    def create_listing(
        self,
        listing: PropertyListing,
        *,
        schema: Schema | None = None,
    ) -> dict[str, Any]:
        active_schema = schema or self.retrieve_schema()
        body = {
            "parent": self._parent_payload(),
            "properties": self.build_page_properties(listing, active_schema),
            "children": self.build_page_children(listing),
        }
        return self._post("/v1/pages", body)

    def build_page_properties(self, listing: PropertyListing, schema: Schema) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        self._put(properties, schema, "title", listing.title, allowed_types={"title"})
        self._put(properties, schema, "external_id", listing.external_id)
        self._put(properties, schema, "source", listing.source_name)
        self._put(properties, schema, "author", listing.author)
        self._put(properties, schema, "posted_at", listing.posted_at, allowed_types={"date", "rich_text"})
        self._put(properties, schema, "url", listing.post_url, allowed_types={"url", "rich_text"})
        self._put(properties, schema, "rent", listing.rent_yen, allowed_types={"number", "rich_text"})
        self._put(properties, schema, "layout", listing.layout)
        self._put(properties, schema, "station", listing.station)
        self._put(properties, schema, "walk", listing.walk_minutes, allowed_types={"number", "rich_text"})
        self._put(properties, schema, "area", listing.area_sqm, allowed_types={"number", "rich_text"})
        self._put(properties, schema, "address", listing.address)
        self._put(properties, schema, "tags", listing.tags, allowed_types={"multi_select", "rich_text"})
        self._put(properties, schema, "body", listing.body)
        self._put(properties, schema, "confidence", listing.confidence, allowed_types={"number", "rich_text"})
        if not properties:
            raise NotionAPIError("No matching Notion properties found. Check docs/notion-schema.md.")
        return properties

    @staticmethod
    def build_page_children(listing: PropertyListing) -> list[dict[str, Any]]:
        facts = [
            f"コミュニティ: {listing.source_name}",
            f"外部ID: {listing.external_id}",
            f"信頼度: {listing.confidence}",
        ]
        if listing.post_url:
            facts.append(f"投稿URL: {listing.post_url}")
        if listing.posted_at:
            facts.append(f"投稿日: {listing.posted_at}")
        return [
            _heading("抽出サマリー"),
            _paragraph("\n".join(facts)),
            _heading("投稿本文"),
            _paragraph(listing.body[:1900]),
        ]

    def _parent_payload(self) -> dict[str, str]:
        if self.config.uses_data_source:
            return {"type": "data_source_id", "data_source_id": self.config.parent_id}
        return {"type": "database_id", "database_id": self.config.parent_id}

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.config.notion_version,
        }

    def _get(self, endpoint: str) -> dict[str, Any]:
        response = self.session.get(
            f"{self.config.base_url.rstrip('/')}{endpoint}",
            headers=self._headers(),
            timeout=self.config.timeout,
        )
        return self._parse_response(response)

    def _post(self, endpoint: str, body: Mapping[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            f"{self.config.base_url.rstrip('/')}{endpoint}",
            headers=self._headers(),
            json=body,
            timeout=self.config.timeout,
        )
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: Any) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if getattr(response, "ok", False):
            return payload if isinstance(payload, dict) else {"raw": payload}
        error = payload.get("message") if isinstance(payload, dict) else None
        message = error or getattr(response, "text", "Unknown Notion API error")
        raise NotionAPIError(
            f"Notion API error status={getattr(response, 'status_code', 'unknown')}: {message}",
            status_code=getattr(response, "status_code", None),
            response=payload,
        )

    def _put(
        self,
        properties: dict[str, Any],
        schema: Schema,
        logical_name: str,
        value: Any,
        *,
        allowed_types: set[str] | None = None,
    ) -> None:
        if value in (None, "", []):
            return
        match = self._find_property(schema, logical_name, allowed_types=allowed_types)
        if match is None:
            return
        property_name, property_type = match
        encoded = _encode_property_value(property_type, value)
        if encoded is not None:
            properties[property_name] = encoded

    @staticmethod
    def _find_property(
        schema: Schema,
        logical_name: str,
        *,
        allowed_types: set[str] | None = None,
    ) -> tuple[str, str] | None:
        aliases = PROPERTY_ALIASES[logical_name]
        for alias in aliases:
            prop = schema.get(alias)
            prop_type = prop.get("type") if isinstance(prop, Mapping) else None
            if isinstance(prop_type, str) and (allowed_types is None or prop_type in allowed_types):
                return alias, prop_type
        if logical_name == "title":
            for name, prop in schema.items():
                prop_type = prop.get("type") if isinstance(prop, Mapping) else None
                if prop_type == "title":
                    return name, prop_type
        return None


def _encode_property_value(property_type: str, value: Any) -> dict[str, Any] | None:
    if property_type == "title":
        return {"title": _rich_text_array(str(value))}
    if property_type == "rich_text":
        text = ", ".join(value) if isinstance(value, list) else str(value)
        return {"rich_text": _rich_text_array(text)}
    if property_type == "url":
        return {"url": str(value)[:2000]}
    if property_type == "number":
        return {"number": float(value)}
    if property_type == "date":
        return {"date": {"start": str(value)}}
    if property_type == "select":
        return {"select": {"name": str(value)[:100]}}
    if property_type == "status":
        return {"status": {"name": str(value)[:100]}}
    if property_type == "multi_select":
        values = value if isinstance(value, list) else [str(value)]
        return {"multi_select": [{"name": str(item)[:100]} for item in values if str(item).strip()]}
    if property_type == "checkbox":
        return {"checkbox": bool(value)}
    return None


def _rich_text_array(text: str) -> list[dict[str, Any]]:
    clean_text = text[:1900]
    return [{"type": "text", "text": {"content": clean_text}}]


def _paragraph(text: str) -> dict[str, Any]:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rich_text_array(text)}}


def _heading(text: str) -> dict[str, Any]:
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": _rich_text_array(text)}}

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

import requests


class HTTPSession(Protocol):
    def post(self, url: str, data: Mapping[str, Any], timeout: int) -> Any: ...


class FacebookAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, response: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


@dataclass
class FacebookPageClient:
    graph_version: str = "v25.0"
    session: HTTPSession | None = None
    timeout: int = 20
    base_url: str = "https://graph.facebook.com"

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

    def publish_feed_post(
        self,
        *,
        page_id: str,
        page_access_token: str,
        message: str | None = None,
        link: str | None = None,
        published: bool = True,
    ) -> dict[str, Any]:
        clean_page_id = page_id.strip()
        clean_token = page_access_token.strip()
        clean_message = message.strip() if isinstance(message, str) and message.strip() else None
        clean_link = link.strip() if isinstance(link, str) and link.strip() else None

        if not clean_page_id:
            raise ValueError("page_id is required")
        if not clean_token:
            raise ValueError("page_access_token is required")
        if not clean_message and not clean_link:
            raise ValueError("message or link is required")

        graph_version = self.graph_version.strip().strip("/")
        url = f"{self.base_url.rstrip('/')}/{graph_version}/{clean_page_id}/feed"
        payload: dict[str, Any] = {
            "access_token": clean_token,
            "published": str(published).lower(),
        }
        if clean_message:
            payload["message"] = clean_message
        if clean_link:
            payload["link"] = clean_link

        assert self.session is not None
        response = self.session.post(url, data=payload, timeout=self.timeout)
        response_data = self._response_json(response)

        if getattr(response, "ok", False):
            if isinstance(response_data, dict):
                return response_data
            return {"raw": response_data}

        raise self._build_error(response, response_data)

    @staticmethod
    def _response_json(response: Any) -> Any:
        try:
            return response.json()
        except ValueError:
            return None

    @staticmethod
    def _build_error(response: Any, response_data: Any) -> FacebookAPIError:
        error = response_data.get("error", {}) if isinstance(response_data, dict) else {}
        message = error.get("message") or getattr(response, "text", "Unknown Facebook API error")
        code = error.get("code")
        status_code = getattr(response, "status_code", None)
        code_part = f" code={code}" if code is not None else ""
        status_part = f" status={status_code}" if status_code is not None else ""
        return FacebookAPIError(
            f"Facebook API error{status_part}{code_part}: {message}",
            status_code=status_code,
            response=response_data,
        )

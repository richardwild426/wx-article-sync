from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class MpTextApiError(RuntimeError):
    pass


Transport = Callable[[str, str, dict[str, str], float], Any]


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    publish_time: int | str | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class Account:
    fakeid: str
    nickname: str | None = None
    raw: dict[str, Any] | None = None


class MpTextClient:
    def __init__(
        self,
        base_url: str,
        auth_key: str,
        *,
        timeout: float = 30.0,
        max_attempts: int = 3,
        retry_sleep_seconds: float = 1.0,
        transport: Transport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth_key = auth_key
        self.timeout = timeout
        self.max_attempts = max(max_attempts, 1)
        self.retry_sleep_seconds = retry_sleep_seconds
        self.transport = transport or self._default_transport

    def validate_auth_key(self) -> None:
        payload = self._get_json("/api/public/v1/authkey")
        if self._response_code(payload) != 0:
            raise MpTextApiError("mptext API key is invalid or expired")

    def search_accounts(self, keyword: str) -> list[Account]:
        payload = self._get_json("/api/public/v1/account", {"keyword": keyword})
        self._raise_for_api_error(payload)
        return [self._account_from_raw(item) for item in self._extract_records(payload)]

    def list_articles(
        self,
        fakeid: str,
        *,
        begin: int = 0,
        size: int = 20,
        keyword: str | None = None,
    ) -> list[Article]:
        params: dict[str, str | int] = {"fakeid": fakeid, "begin": begin, "size": size}
        if keyword:
            params["keyword"] = keyword
        payload = self._get_json("/api/public/v1/article", params)
        self._raise_for_api_error(payload)
        return [self._article_from_raw(item) for item in self._extract_records(payload)]

    def download_article(self, url: str, content_format: str = "html") -> str:
        payload = self._get("/api/public/v1/download", {"url": url, "format": content_format})
        if isinstance(payload, str):
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                return payload
            return self._extract_content(decoded)
        return self._extract_content(payload)

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = self._get(path, params)
        if not isinstance(payload, dict):
            raise MpTextApiError(f"Expected JSON object from {path}")
        return payload

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.transport("GET", url, self._headers(), self.timeout)
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_attempts:
                    break
                if self.retry_sleep_seconds > 0:
                    time.sleep(self.retry_sleep_seconds)
        assert last_error is not None
        raise last_error

    def _headers(self) -> dict[str, str]:
        return {
            "X-Auth-Key": self.auth_key,
            "Accept": "application/json",
            "User-Agent": "wx-article-sync/0.1 (+https://docs.mptext.top/advanced/api.html)",
        }

    @staticmethod
    def _default_transport(method: str, url: str, headers: dict[str, str], timeout: float) -> Any:
        request = Request(url, method=method, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise MpTextApiError(f"HTTP {exc.code} from mptext API: {exc.reason}") from exc
        except URLError as exc:
            raise MpTextApiError(f"Failed to connect to mptext API: {exc.reason}") from exc
        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type:
            return json.loads(body)
        return body

    @staticmethod
    def _response_code(payload: dict[str, Any]) -> int | None:
        code = payload.get("code")
        return code if isinstance(code, int) else None

    @classmethod
    def _raise_for_api_error(cls, payload: dict[str, Any]) -> None:
        code = cls._response_code(payload)
        if code not in (None, 0):
            message = payload.get("message") or payload.get("msg") or "mptext API request failed"
            raise MpTextApiError(str(message))

    @classmethod
    def _extract_records(cls, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("list", "items", "articles", "accounts", "account_list", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        data = payload.get("data")
        if data is not payload:
            return cls._extract_records(data)
        return []

    @staticmethod
    def _article_from_raw(raw: dict[str, Any]) -> Article:
        url = raw.get("url") or raw.get("link") or raw.get("content_url") or raw.get("app_msg_url")
        if not isinstance(url, str) or not url:
            raise MpTextApiError("Article record is missing url")
        title = raw.get("title") or raw.get("appmsg_title") or raw.get("name") or url
        publish_time = raw.get("publish_time") or raw.get("create_time") or raw.get("datetime")
        return Article(title=str(title), url=url, publish_time=publish_time, raw=raw)

    @staticmethod
    def _account_from_raw(raw: dict[str, Any]) -> Account:
        fakeid = raw.get("fakeid") or raw.get("fake_id") or raw.get("id")
        if not isinstance(fakeid, str) or not fakeid:
            raise MpTextApiError("Account record is missing fakeid")
        nickname = raw.get("nickname") or raw.get("name") or raw.get("alias")
        return Account(fakeid=fakeid, nickname=str(nickname) if nickname else None, raw=raw)

    @staticmethod
    def _extract_content(payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if not isinstance(payload, dict):
            raise MpTextApiError("Download response does not contain article content")
        code = payload.get("code")
        if isinstance(code, int) and code != 0:
            message = payload.get("message") or payload.get("msg") or "article download failed"
            raise MpTextApiError(str(message))
        for key in ("content", "html", "markdown", "text"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        data = payload.get("data")
        if data is not payload:
            return MpTextClient._extract_content(data)
        raise MpTextApiError("Download response does not contain article content")

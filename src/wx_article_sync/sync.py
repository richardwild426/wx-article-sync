from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .client import Article, MpTextApiError, MpTextClient
from .config import AccountConfig, SyncConfig


@dataclass(frozen=True)
class SyncResult:
    scanned: int = 0
    downloaded: int = 0
    skipped: int = 0


class ArticleSyncer:
    def __init__(self, config: SyncConfig, *, client: MpTextClient | None = None) -> None:
        self.config = config
        self.client = client or MpTextClient(
            config.api_base_url,
            config.api_key,
            timeout=config.timeout_seconds,
        )

    def run_once(self, *, validate_auth: bool = True) -> SyncResult:
        if validate_auth:
            self.client.validate_auth_key()
        state = self._load_state()
        seen_urls = set(state.get("seen_urls", []))
        scanned = downloaded = skipped = 0

        for account in self.config.accounts:
            fakeid = self._resolve_fakeid(account)
            for page in range(self.config.max_pages):
                begin = page * self.config.page_size
                articles = self.client.list_articles(
                    fakeid,
                    begin=begin,
                    size=self.config.page_size,
                    keyword=account.article_keyword,
                )
                if not articles:
                    break
                scanned += len(articles)
                for article in articles:
                    if article.url in seen_urls:
                        skipped += 1
                        continue
                    content = self.client.download_article(article.url, self.config.content_format)
                    self._save_article(article, content, fakeid)
                    seen_urls.add(article.url)
                    downloaded += 1

        self._save_state({"seen_urls": sorted(seen_urls), "updated_at": _utc_now()})
        return SyncResult(scanned=scanned, downloaded=downloaded, skipped=skipped)

    def _resolve_fakeid(self, account: AccountConfig) -> str:
        if account.fakeid:
            return account.fakeid
        if not account.keyword:
            raise MpTextApiError("Account is missing both fakeid and keyword")
        matches = self.client.search_accounts(account.keyword)
        if not matches:
            raise MpTextApiError(f"No account found for keyword: {account.keyword}")
        return matches[0].fakeid

    def _load_state(self) -> dict[str, Any]:
        if not self.config.state_path.exists():
            return {"seen_urls": []}
        return json.loads(self.config.state_path.read_text(encoding="utf-8"))

    def _save_state(self, state: dict[str, Any]) -> None:
        self.config.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(self.config.state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    def _save_article(self, article: Article, content: str, fakeid: str) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        stem = self._article_stem(article)
        content_path = self.config.output_dir / f"{stem}.{self._extension()}"
        metadata_path = self.config.output_dir / f"{stem}.json"
        metadata = {
            "title": article.title,
            "url": article.url,
            "publish_time": article.publish_time,
            "fakeid": fakeid,
            "format": self.config.content_format,
            "synced_at": _utc_now(),
            "raw": article.raw,
        }
        self._atomic_write(content_path, content)
        self._atomic_write(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")

    def _article_stem(self, article: Article) -> str:
        digest = hashlib.sha1(article.url.encode("utf-8")).hexdigest()[:10]
        title = re.sub(r"[^0-9A-Za-z._-]+", "-", article.title).strip("-").lower()
        if not title:
            title = "article"
        return f"{self._publish_prefix(article)}-{title[:80]}-{digest}"

    @staticmethod
    def _publish_prefix(article: Article) -> str:
        value = article.publish_time
        if isinstance(value, int):
            return datetime.fromtimestamp(value, UTC).strftime("%Y%m%d")
        if isinstance(value, str) and value:
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 8:
                return digits[:8]
        return datetime.now(UTC).strftime("%Y%m%d")

    def _extension(self) -> str:
        return {"markdown": "md", "html": "html", "text": "txt", "json": "json"}.get(
            self.config.content_format,
            "txt",
        )

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent)) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")

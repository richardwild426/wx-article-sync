from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .client import Article, MpTextApiError, MpTextClient
from .config import AccountConfig, SyncConfig
from .logging import get_logger
from .pdf import PdfConverter, PlaywrightPdfConverter


logger = get_logger("sync")


@dataclass(frozen=True)
class SyncResult:
    scanned: int = 0
    downloaded: int = 0
    skipped: int = 0


class ArticleSyncer:
    def __init__(
        self,
        config: SyncConfig,
        *,
        client: MpTextClient | None = None,
        pdf_converter: PdfConverter | None = None,
    ) -> None:
        self.config = config
        self.client = client or MpTextClient(
            config.api_base_url,
            config.api_key,
            timeout=config.timeout_seconds,
        )
        self.pdf_converter = pdf_converter or PlaywrightPdfConverter()

    def run_once(self, *, validate_auth: bool = True) -> SyncResult:
        logger.info(
            "Starting sync accounts=%s page_size=%s max_pages=%s format=%s output_dir=%s",
            len(self.config.accounts),
            self.config.page_size,
            self.config.max_pages,
            self.config.content_format,
            self.config.output_dir,
        )
        if validate_auth:
            self.client.validate_auth_key()
        state = self._load_state()
        seen_urls = set(state.get("seen_urls", []))
        scanned = downloaded = skipped = 0

        for account in self.config.accounts:
            fakeid = self._resolve_fakeid(account)
            logger.info("Syncing account fakeid=%s", fakeid)
            for page in range(self.config.max_pages):
                begin = page * self.config.page_size
                logger.info("Listing articles fakeid=%s page=%s begin=%s size=%s", fakeid, page + 1, begin, self.config.page_size)
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
                        logger.info("Skipping already synced article title=%s", article.title)
                        continue
                    logger.info("Downloading article title=%s format=%s", article.title, self.config.content_format)
                    content = self.client.download_article(article.url, self.config.content_format)
                    self._save_article(article, content, fakeid)
                    seen_urls.add(article.url)
                    downloaded += 1

        self._save_state({"seen_urls": sorted(seen_urls), "updated_at": _utc_now()})
        logger.info("Saved sync state path=%s seen_urls=%s", self.config.state_path, len(seen_urls))
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
        article_dir = self.config.output_dir / self._article_dir_name(article)
        article_dir.mkdir(parents=True, exist_ok=True)
        content_path = article_dir / f"article.{self._extension()}"
        metadata_path = article_dir / "metadata.json"
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
        logger.info("Saved article title=%s dir=%s content=%s metadata=%s", article.title, article_dir, content_path, metadata_path)
        if self.config.content_format == "html":
            pdf_path = article_dir / f"{article_dir.name}.pdf"
            logger.info("Converting article HTML to PDF title=%s html=%s pdf=%s", article.title, content_path, pdf_path)
            self.pdf_converter.convert(content_path, pdf_path, self.config.output_dir)
            logger.info("Converted article PDF title=%s pdf=%s", article.title, pdf_path)

    def _article_dir_name(self, article: Article) -> str:
        title = _safe_path_name(article.title)
        if not title:
            title = "article"
        return f"{self._publish_date(article)}_{title[:120]}"

    @staticmethod
    def _publish_date(article: Article) -> str:
        value = article.publish_time
        if isinstance(value, int):
            return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%d")
        if isinstance(value, str) and value:
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 8:
                return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return datetime.now(UTC).strftime("%Y-%m-%d")

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


def _safe_path_name(value: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", value)
    name = re.sub(r"\s+", " ", name).strip(" ._")
    return name

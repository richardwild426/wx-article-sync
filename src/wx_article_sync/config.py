from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AccountConfig:
    fakeid: str | None = None
    keyword: str | None = None
    article_keyword: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AccountConfig":
        fakeid = payload.get("fakeid")
        keyword = payload.get("keyword")
        if not fakeid and not keyword:
            raise ConfigError("Each account must define either fakeid or keyword")
        return cls(
            fakeid=str(fakeid) if fakeid else None,
            keyword=str(keyword) if keyword else None,
            article_keyword=str(payload["article_keyword"]) if payload.get("article_keyword") else None,
        )


@dataclass(frozen=True)
class SyncConfig:
    api_base_url: str
    api_key: str
    output_dir: Path
    state_path: Path
    accounts: list[AccountConfig] = field(default_factory=list)
    content_format: str = "markdown"
    interval_seconds: int = 3600
    page_size: int = 20
    max_pages: int = 1
    timeout_seconds: float = 30.0

    @classmethod
    def from_file(cls, path: str | Path) -> "SyncConfig":
        config_path = Path(path).expanduser().resolve()
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        base_dir = config_path.parent
        api_key_env = payload.get("api_key_env", "MP_TEXT_API_KEY")
        api_key = payload.get("api_key") or os.environ.get(str(api_key_env))
        if not api_key:
            raise ConfigError(f"Missing API key. Set {api_key_env} or api_key in config.")
        accounts_payload = payload.get("accounts")
        if not isinstance(accounts_payload, list) or not accounts_payload:
            raise ConfigError("Config must include at least one account")
        output_dir = cls._resolve_path(base_dir, payload.get("output_dir", "data/articles"))
        state_path = cls._resolve_path(base_dir, payload.get("state_path", "data/state.json"))
        return cls(
            api_base_url=str(payload.get("api_base_url", "https://down.mptext.top")),
            api_key=str(api_key),
            output_dir=output_dir,
            state_path=state_path,
            accounts=[AccountConfig.from_dict(item) for item in accounts_payload],
            content_format=str(payload.get("content_format", "markdown")),
            interval_seconds=int(payload.get("interval_seconds", 3600)),
            page_size=min(int(payload.get("page_size", 20)), 20),
            max_pages=max(int(payload.get("max_pages", 1)), 1),
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )

    @staticmethod
    def _resolve_path(base_dir: Path, value: str | Path) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else base_dir / path

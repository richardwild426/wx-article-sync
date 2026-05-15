#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


VALID_FORMATS = {"markdown", "html", "text", "json"}
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HEX_SECRET_RE = re.compile(r"^[A-Fa-f0-9]{24,}$")


class ValidationError(ValueError):
    pass


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: validate_config.py <config.json>", file=sys.stderr)
        return 2

    path = Path(argv[1]).expanduser()
    try:
        payload = _load_json(path)
        summary = validate_config(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"Config invalid: {exc}", file=sys.stderr)
        return 2

    print(
        "Config OK: "
        f"accounts={summary['accounts']} "
        f"page_size={summary['page_size']} "
        f"max_pages={summary['max_pages']} "
        f"format={summary['content_format']}"
    )
    if summary["daily_latest"]:
        print("This matches a daily latest article setup.")
    return 0


def validate_config(payload: dict[str, Any]) -> dict[str, Any]:
    accounts = payload.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        raise ValidationError("accounts must be a non-empty list")

    for index, account in enumerate(accounts, start=1):
        if not isinstance(account, dict):
            raise ValidationError(f"accounts[{index}] must be an object")
        fakeid = account.get("fakeid")
        keyword = account.get("keyword")
        if not fakeid and not keyword:
            raise ValidationError(f"accounts[{index}] must define fakeid or keyword")
        if fakeid and keyword:
            raise ValidationError(f"accounts[{index}] should not define both fakeid and keyword")
        if "article_keyword" in account and not isinstance(account["article_keyword"], str):
            raise ValidationError(f"accounts[{index}].article_keyword must be a string")
        exclude_title_keywords = account.get("exclude_title_keywords", [])
        if isinstance(exclude_title_keywords, str):
            continue
        if not isinstance(exclude_title_keywords, list) or any(
            not isinstance(keyword, str) for keyword in exclude_title_keywords
        ):
            raise ValidationError(f"accounts[{index}].exclude_title_keywords must be a string or list of strings")

    api_key = payload.get("api_key")
    api_key_env = payload.get("api_key_env", "MP_TEXT_API_KEY")
    if not api_key and not api_key_env:
        raise ValidationError("config must define api_key or api_key_env")
    if api_key_env and (
        not isinstance(api_key_env, str)
        or not ENV_NAME_RE.match(api_key_env)
        or HEX_SECRET_RE.match(api_key_env)
    ):
        raise ValidationError("api_key_env must be an environment variable name, not the key value")

    page_size = _positive_int(payload.get("page_size", 20), "page_size")
    if page_size > 20:
        raise ValidationError("page_size must be 20 or less")
    max_pages = _positive_int(payload.get("max_pages", 1), "max_pages")

    content_format = str(payload.get("content_format", "markdown"))
    if content_format not in VALID_FORMATS:
        raise ValidationError(f"content_format must be one of: {', '.join(sorted(VALID_FORMATS))}")

    return {
        "accounts": len(accounts),
        "page_size": page_size,
        "max_pages": max_pages,
        "content_format": content_format,
        "daily_latest": page_size == 1 and max_pages == 1,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError("config root must be a JSON object")
    return payload


def _positive_int(value: Any, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be a positive integer") from exc
    if parsed < 1:
        raise ValidationError(f"{name} must be a positive integer")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

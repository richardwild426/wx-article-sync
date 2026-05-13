#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: inspect_state.py <state.json>", file=sys.stderr)
        return 2

    path = Path(argv[1]).expanduser()
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"State invalid: {exc}", file=sys.stderr)
        return 2

    seen_urls = payload.get("seen_urls", [])
    updated_at = payload.get("updated_at", "unknown")
    print(f"State OK: seen_urls={len(seen_urls)} updated_at={updated_at}")
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("state root must be a JSON object")
    seen_urls = payload.get("seen_urls", [])
    if not isinstance(seen_urls, list):
        raise ValueError("seen_urls must be a list")
    return payload


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build an IMA import manifest from saved wx-article-sync articles.")
    parser.add_argument("articles_dir", help="Path to the local articles directory, usually data/articles.")
    parser.add_argument("--include-url", action="store_true", help="Include source_url in JSONL output.")
    parser.add_argument("--output", help="Write JSONL to this path instead of stdout.")
    args = parser.parse_args(argv[1:])

    try:
        rows = list(build_manifest(Path(args.articles_dir), include_url=args.include_url))
    except (OSError, ValueError) as exc:
        print(f"IMA manifest failed: {exc}", file=sys.stderr)
        return 2

    output = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"IMA manifest written: path={output_path} articles={len(rows)}", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0


def build_manifest(articles_dir: Path, *, include_url: bool = False) -> list[dict[str, Any]]:
    if not articles_dir.exists():
        raise ValueError(f"articles_dir does not exist: {articles_dir}")
    if not articles_dir.is_dir():
        raise ValueError(f"articles_dir is not a directory: {articles_dir}")

    rows: list[dict[str, Any]] = []
    for metadata_path in sorted(articles_dir.glob("*/metadata.json")):
        metadata = _read_json(metadata_path)
        content_path = _find_content_path(metadata_path.parent)
        if content_path is None:
            continue
        file_name = content_path.name
        row: dict[str, Any] = {
            "title": file_name,
            "file_name": file_name,
            "original_title": str(metadata.get("title") or metadata_path.parent.name),
            "content_path": str(content_path),
            "metadata_path": str(metadata_path),
            "article_dir": str(metadata_path.parent),
            "content_format": str(metadata.get("format") or content_path.suffix.lstrip(".")),
            "publish_time": metadata.get("publish_time"),
            "synced_at": metadata.get("synced_at"),
            "ima_module": "knowledge-base",
            "ima_workflow": "create_media -> COS -> add_knowledge",
        }
        if include_url and metadata.get("url"):
            row["source_url"] = str(metadata["url"])
        rows.append(row)
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"metadata root must be an object: {path}")
    return payload


def _find_content_path(article_dir: Path) -> Path | None:
    for name in ("article.md", "article.html", "article.txt", "article.json"):
        path = article_dir / name
        if path.is_file():
            return path
    return None


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

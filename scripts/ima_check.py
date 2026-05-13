#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    client_id = _read_credential("IMA_OPENAPI_CLIENTID", Path("~/.config/ima/client_id").expanduser())
    api_key = _read_credential("IMA_OPENAPI_APIKEY", Path("~/.config/ima/api_key").expanduser())
    if not client_id or not api_key:
        print(
            "IMA credentials missing. Configure IMA_OPENAPI_CLIENTID and IMA_OPENAPI_APIKEY, "
            "or write them to ~/.config/ima/client_id and ~/.config/ima/api_key.",
            file=sys.stderr,
        )
        return 2
    print("IMA credentials OK: source=environment_or_config")
    return 0


def _read_credential(env_name: str, path: Path) -> str | None:
    value = os.environ.get(env_name)
    if value:
        return value.strip()
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())


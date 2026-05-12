from __future__ import annotations

import argparse
import time

from .config import ConfigError, SyncConfig
from .logging import configure_logging, get_logger
from .sync import ArticleSyncer


logger = get_logger("cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize WeChat articles from the mptext API.")
    parser.add_argument("--config", default="config.json", help="Path to JSON config file.")
    parser.add_argument("--daemon", action="store_true", help="Run forever on interval_seconds.")
    parser.add_argument("--skip-auth-check", action="store_true", help="Skip /authkey validation before syncing.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level)
    try:
        config = SyncConfig.from_file(args.config)
    except (ConfigError, OSError, ValueError) as exc:
        logger.error("Failed to load config: %s", exc)
        return 2

    syncer = ArticleSyncer(config)
    while True:
        try:
            result = syncer.run_once(validate_auth=not args.skip_auth_check)
        except Exception:
            logger.exception("Sync failed")
            if not args.daemon:
                return 1
        else:
            logger.info(
                "Sync finished: scanned=%s downloaded=%s skipped=%s",
                result.scanned,
                result.downloaded,
                result.skipped,
            )
        if not args.daemon:
            return 0
        time.sleep(config.interval_seconds)

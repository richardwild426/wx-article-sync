import logging
import tempfile
import unittest
from logging.handlers import RotatingFileHandler
from pathlib import Path

from wx_article_sync.logging import LOG_FILE_MAX_BYTES, configure_logging, get_logger


class LoggingConfigTest(unittest.TestCase):
    def test_configure_logging_persists_logs_with_two_mb_rotation_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "sync.log"

            configure_logging("INFO", log_path=log_path)
            get_logger("test").info("persisted message")
            for handler in logging.getLogger().handlers:
                handler.flush()

            self.assertIn("persisted message", log_path.read_text(encoding="utf-8"))
            file_handlers = [
                handler
                for handler in logging.getLogger().handlers
                if isinstance(handler, RotatingFileHandler)
            ]
            self.assertEqual(len(file_handlers), 1)
            self.assertEqual(file_handlers[0].maxBytes, LOG_FILE_MAX_BYTES)
            self.assertEqual(LOG_FILE_MAX_BYTES, 2 * 1024 * 1024)
            logging.basicConfig(handlers=[], force=True)


if __name__ == "__main__":
    unittest.main()

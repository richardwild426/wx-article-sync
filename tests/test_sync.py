import json
import os
import tempfile
import unittest
from pathlib import Path

from wx_article_sync.client import MpTextClient
from wx_article_sync.config import AccountConfig, SyncConfig
from wx_article_sync.sync import ArticleSyncer


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def __call__(self, method, url, headers, timeout):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class MpTextClientTest(unittest.TestCase):
    def test_sends_auth_key_and_query_parameters(self):
        transport = FakeTransport([{"code": 0, "data": []}])
        client = MpTextClient(
            base_url="https://down.mptext.top",
            auth_key="secret-key",
            transport=transport,
        )

        client.list_articles("fake-id", begin=20, size=20, keyword="AI")

        request = transport.requests[0]
        self.assertEqual(request["headers"]["X-Auth-Key"], "secret-key")
        self.assertIn("wx-article-sync", request["headers"]["User-Agent"])
        self.assertEqual(request["headers"]["Accept"], "application/json")
        self.assertIn("/api/public/v1/article?", request["url"])
        self.assertIn("fakeid=fake-id", request["url"])
        self.assertIn("begin=20", request["url"])
        self.assertIn("size=20", request["url"])
        self.assertIn("keyword=AI", request["url"])

    def test_extracts_download_content_from_json_wrapper(self):
        transport = FakeTransport([{"code": 0, "data": {"content": "# Title"}}])
        client = MpTextClient(
            base_url="https://down.mptext.top",
            auth_key="secret-key",
            transport=transport,
        )

        content = client.download_article("https://mp.weixin.qq.com/s/x", "markdown")

        self.assertEqual(content, "# Title")

    def test_retries_transient_connection_errors(self):
        transport = FakeTransport(
            [
                Exception("temporary connection reset"),
                {"code": 0, "data": {"content": "# Title"}},
            ]
        )
        client = MpTextClient(
            base_url="https://down.mptext.top",
            auth_key="secret-key",
            transport=transport,
            retry_sleep_seconds=0,
        )

        content = client.download_article("https://mp.weixin.qq.com/s/x", "markdown")

        self.assertEqual(content, "# Title")
        self.assertEqual(len(transport.requests), 2)


class ArticleSyncerTest(unittest.TestCase):
    def test_sync_downloads_new_articles_and_skips_existing_urls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "articles"
            state_path = Path(tmpdir) / "state.json"
            transport = FakeTransport(
                [
                    {"code": 0},
                    {
                        "code": 0,
                        "data": {
                            "list": [
                                {
                                    "title": "First Article",
                                    "url": "https://mp.weixin.qq.com/s/first",
                                    "publish_time": 1710000000,
                                }
                            ]
                        },
                    },
                    "# First Article\n\nBody",
                    {
                        "code": 0,
                        "data": {
                            "list": [
                                {
                                    "title": "First Article",
                                    "url": "https://mp.weixin.qq.com/s/first",
                                    "publish_time": 1710000000,
                                }
                            ]
                        },
                    },
                ]
            )
            config = SyncConfig(
                api_base_url="https://down.mptext.top",
                api_key="secret-key",
                output_dir=output_dir,
                state_path=state_path,
                content_format="markdown",
                accounts=[AccountConfig(fakeid="fake-id")],
                max_pages=1,
            )
            syncer = ArticleSyncer(config, client=MpTextClient(config.api_base_url, config.api_key, transport=transport))

            first_result = syncer.run_once()
            second_result = syncer.run_once(validate_auth=False)

            self.assertEqual(first_result.downloaded, 1)
            self.assertEqual(second_result.downloaded, 0)
            markdown_files = sorted(output_dir.glob("*.md"))
            metadata_files = sorted(output_dir.glob("*.json"))
            self.assertEqual(len(markdown_files), 1)
            self.assertEqual(markdown_files[0].read_text(encoding="utf-8"), "# First Article\n\nBody")
            metadata = json.loads(metadata_files[0].read_text(encoding="utf-8"))
            self.assertEqual(metadata["url"], "https://mp.weixin.qq.com/s/first")
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIn("https://mp.weixin.qq.com/s/first", state["seen_urls"])

    def test_resolves_account_keyword_to_first_fakeid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transport = FakeTransport(
                [
                    {"code": 0},
                    {
                        "code": 0,
                        "data": {
                            "accounts": [
                                {"nickname": "Example Account", "fakeid": "resolved-fake-id"}
                            ]
                        },
                    },
                    {"code": 0, "data": {"list": []}},
                ]
            )
            config = SyncConfig(
                api_base_url="https://down.mptext.top",
                api_key="secret-key",
                output_dir=Path(tmpdir) / "articles",
                state_path=Path(tmpdir) / "state.json",
                accounts=[AccountConfig(keyword="Example")],
            )
            syncer = ArticleSyncer(config, client=MpTextClient(config.api_base_url, config.api_key, transport=transport))

            result = syncer.run_once()

            self.assertEqual(result.scanned, 0)
            article_request = transport.requests[-1]["url"]
            self.assertIn("fakeid=resolved-fake-id", article_request)

    def test_config_reads_api_key_from_environment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "api_base_url": "https://down.mptext.top",
                        "api_key_env": "MP_TEXT_API_KEY_FOR_TEST",
                        "output_dir": "articles",
                        "state_path": "state.json",
                        "accounts": [{"fakeid": "fake-id"}],
                    }
                ),
                encoding="utf-8",
            )
            os.environ["MP_TEXT_API_KEY_FOR_TEST"] = "secret-key"
            try:
                config = SyncConfig.from_file(config_path)
            finally:
                os.environ.pop("MP_TEXT_API_KEY_FOR_TEST", None)

            self.assertEqual(config.api_key, "secret-key")
            self.assertEqual(config.output_dir, (Path(tmpdir) / "articles").resolve())

    def test_config_error_does_not_echo_api_key_env_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            misplaced_secret = "ab7c5801d4ad49f18322318f96c5d6a0"
            config_path.write_text(
                json.dumps(
                    {
                        "api_key_env": misplaced_secret,
                        "accounts": [{"fakeid": "fake-id"}],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(Exception) as context:
                SyncConfig.from_file(config_path)

            message = str(context.exception)
            self.assertIn("api_key", message)
            self.assertNotIn(misplaced_secret, message)


if __name__ == "__main__":
    unittest.main()

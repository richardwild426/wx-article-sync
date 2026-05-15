import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_CONFIG = ROOT / "scripts" / "validate_config.py"
INSPECT_STATE = ROOT / "scripts" / "inspect_state.py"
IMA_CHECK = ROOT / "scripts" / "ima_check.py"
IMA_MANIFEST = ROOT / "scripts" / "ima_manifest.py"


class SkillScriptTest(unittest.TestCase):
    def test_skill_package_matches_agentskills_shape(self):
        skill_dir = ROOT
        skill_md = ROOT / "SKILL.md"
        text = skill_md.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]

        self.assertIn("name: wx-article-sync", frontmatter)
        self.assertIn("description:", frontmatter)
        self.assertIn("compatibility:", frontmatter)
        self.assertTrue((skill_dir / "references" / "configuration.md").is_file())
        self.assertTrue((skill_dir / "references" / "operations.md").is_file())
        self.assertTrue((skill_dir / "references" / "troubleshooting.md").is_file())
        self.assertTrue((skill_dir / "assets" / "config.example.json").is_file())
        self.assertTrue(os.access(VALIDATE_CONFIG, os.X_OK))
        self.assertTrue(os.access(INSPECT_STATE, os.X_OK))
        self.assertTrue((skill_dir / "references" / "ima.md").is_file())
        self.assertTrue(os.access(IMA_CHECK, os.X_OK))
        self.assertTrue(os.access(IMA_MANIFEST, os.X_OK))

    def test_validate_config_accepts_minimal_business_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "api_key_env": "MP_TEXT_API_KEY",
                        "page_size": 1,
                        "max_pages": 1,
                        "accounts": [
                            {"fakeid": "MzkyMjUxNDU5Nw=="},
                            {"fakeid": "Mzg3NzcyMjE5Mg=="},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self._run(VALIDATE_CONFIG, config_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Config OK", result.stdout)
            self.assertIn("accounts=2", result.stdout)
            self.assertIn("daily latest article setup", result.stdout)

    def test_validate_config_rejects_missing_accounts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(json.dumps({"api_key_env": "MP_TEXT_API_KEY"}), encoding="utf-8")

            result = self._run(VALIDATE_CONFIG, config_path)

            self.assertEqual(result.returncode, 2)
            self.assertIn("accounts must be a non-empty list", result.stderr)

    def test_validate_config_rejects_api_key_env_that_looks_like_a_secret(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "api_key_env": "ab7c5801d4ad49f18322318f96c5d6a0",
                        "accounts": [{"fakeid": "MzkyMjUxNDU5Nw=="}],
                    }
                ),
                encoding="utf-8",
            )

            result = self._run(VALIDATE_CONFIG, config_path)

            self.assertEqual(result.returncode, 2)
            self.assertIn("api_key_env must be an environment variable name", result.stderr)
            self.assertNotIn("ab7c5801", result.stderr)

    def test_validate_config_rejects_invalid_exclude_title_keywords(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "api_key_env": "MP_TEXT_API_KEY",
                        "accounts": [
                            {
                                "fakeid": "MzkyMjUxNDU5Nw==",
                                "exclude_title_keywords": ["广告", 123],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self._run(VALIDATE_CONFIG, config_path)

            self.assertEqual(result.returncode, 2)
            self.assertIn("exclude_title_keywords must be a string or list of strings", result.stderr)

    def test_inspect_state_summarizes_without_printing_full_urls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "updated_at": "2026-05-13T00:00:00Z",
                        "seen_urls": [
                            "https://mp.weixin.qq.com/s/first-secret-token",
                            "https://mp.weixin.qq.com/s/second-secret-token",
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self._run(INSPECT_STATE, state_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("seen_urls=2", result.stdout)
            self.assertIn("updated_at=2026-05-13T00:00:00Z", result.stdout)
            self.assertNotIn("first-secret-token", result.stdout)
            self.assertNotIn("second-secret-token", result.stdout)

    def test_ima_check_reports_missing_credentials_without_printing_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [sys.executable, str(IMA_CHECK)],
                check=False,
                capture_output=True,
                text=True,
                env={"PATH": os.environ.get("PATH", ""), "HOME": tmpdir},
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("IMA credentials missing", result.stderr)
        self.assertNotIn("IMA_OPENAPI_APIKEY=", result.stderr)

    def test_ima_check_accepts_environment_credentials_without_echoing_them(self):
        env = {
            "PATH": os.environ.get("PATH", ""),
            "IMA_OPENAPI_CLIENTID": "client-id-for-test",
            "IMA_OPENAPI_APIKEY": "api-key-for-test",
        }

        result = subprocess.run(
            [sys.executable, str(IMA_CHECK)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("IMA credentials OK", result.stdout)
        self.assertNotIn("client-id-for-test", result.stdout)
        self.assertNotIn("api-key-for-test", result.stdout)

    def test_ima_manifest_lists_saved_articles_without_url_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            articles_dir = Path(tmpdir) / "articles"
            article_dir = articles_dir / "2026-05-13_Test Article"
            article_dir.mkdir(parents=True)
            content_path = article_dir / "article.md"
            metadata_path = article_dir / "metadata.json"
            content_path.write_text("# Test Article\n\nBody", encoding="utf-8")
            metadata_path.write_text(
                json.dumps(
                    {
                        "title": "Test Article",
                        "url": "https://mp.weixin.qq.com/s/secret-token",
                        "publish_time": 1710000000,
                        "format": "markdown",
                        "synced_at": "2026-05-13T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )

            result = self._run(IMA_MANIFEST, articles_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["title"], "article.md")
            self.assertEqual(rows[0]["file_name"], "article.md")
            self.assertEqual(rows[0]["original_title"], "Test Article")
            self.assertEqual(rows[0]["content_path"], str(content_path))
            self.assertEqual(rows[0]["ima_module"], "knowledge-base")
            self.assertEqual(rows[0]["ima_workflow"], "create_media -> COS -> add_knowledge")
            self.assertNotIn("source_url", rows[0])
            self.assertNotIn("secret-token", result.stdout)

    def test_ima_reference_routes_to_official_knowledge_base_skill(self):
        text = (ROOT / "references" / "ima.md").read_text(encoding="utf-8")

        self.assertIn("knowledge-base/SKILL.md", text)
        self.assertIn("create_media → COS → add_knowledge", text)
        self.assertIn("title` 必须等于 `file_name", text)
        self.assertIn("不支持视频文件、Bilibili/YouTube URL 和 `file://` URL", text)

    def test_skill_guides_install_success_with_conversation_not_technical_dump(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("安装完成后的回复", text)
        self.assertIn("不要输出克隆路径", text)
        self.assertIn("不要列出依赖包", text)
        self.assertIn("一次只问一个问题", text)
        self.assertIn("你想同步几个公众号", text)

    def test_skill_guides_user_to_choose_sync_article_count(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        config_text = (ROOT / "references" / "configuration.md").read_text(encoding="utf-8")

        self.assertIn("默认每个公众号每次最多请求 20 篇", skill_text)
        self.assertIn("每天同步最新 1 篇", skill_text)
        self.assertIn("默认每个公众号每次最多请求 20 篇", config_text)
        self.assertIn("如果用户没有明确选择，不要静默沿用默认 20 篇", config_text)

    def test_skill_install_flow_requires_prerequisites_then_initialization(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("先确认前置要求", skill_text)
        self.assertIn("mptext 前置准备完成了吗", skill_text)
        self.assertIn("初始化设置", skill_text)
        self.assertIn("需要同步的公众号", skill_text)
        self.assertIn("同步的文章数量", skill_text)
        self.assertIn("同步频率", skill_text)
        self.assertIn("是否需要联动 IMA", skill_text)
        self.assertIn("IMA 怎么配置", skill_text)

    def test_skill_disambiguates_config_workspace_from_project_root(self):
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        operations_text = (ROOT / "references" / "operations.md").read_text(encoding="utf-8")

        self.assertIn("CONFIG_PATH", skill_text)
        self.assertIn("--config` 传入 `CONFIG_PATH` 的绝对路径", skill_text)
        self.assertIn("不要把配置复制到源码目录", skill_text)
        self.assertIn("uv run wx-article-sync --config /absolute/path/to/config.json", operations_text)
        self.assertIn("Relative `output_dir` and `state_path` values are resolved", operations_text)

    @staticmethod
    def _run(script: Path, *args: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *(str(arg) for arg in args)],
            check=False,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    unittest.main()

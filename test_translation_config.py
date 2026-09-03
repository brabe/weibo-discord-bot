from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from core.config import load_config


BASE_CONFIG = """
[weibo]
  [weibo.test]
    read_link_url = \"https://weibo.com/u/123456\"
    message_webhook = \"https://discord.com/api/webhooks/a/b\"

[status]
  enabled = false
"""


class TranslationConfigTests(unittest.TestCase):
    def _write_config(self, content: str) -> str:
        handle, path = tempfile.mkstemp(suffix=".toml")
        os.close(handle)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _clean_env(self) -> dict[str, str]:
        return {k: v for k, v in os.environ.items() if not k.startswith("WEIBO_")}

    def test_translation_defaults_when_missing(self) -> None:
        config_path = self._write_config(BASE_CONFIG)
        env = self._clean_env()
        env["WEIBO_CONFIG_FILE"] = config_path

        with patch.dict(os.environ, env, clear=True):
            cfg = load_config()

        self.assertIn("translation", cfg)
        self.assertFalse(cfg["translation"]["enabled"])
        self.assertEqual(cfg["translation"]["provider"], "googletrans")
        self.assertEqual(cfg["translation"]["timeout_seconds"], 8)

    def test_translation_enabled_requires_target(self) -> None:
        config_path = self._write_config(
            BASE_CONFIG
            + """
[translation]
  enabled = true
"""
        )
        env = self._clean_env()
        env["WEIBO_CONFIG_FILE"] = config_path

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                load_config()

    def test_translation_target_env_overrides_toml(self) -> None:
        config_path = self._write_config(
            BASE_CONFIG
            + """
[translation]
  enabled = true
  target_language = \"ja\"
"""
        )
        env = self._clean_env()
        env["WEIBO_CONFIG_FILE"] = config_path
        env["WEIBO_TRANSLATION_TARGET_LANGUAGE"] = "en"

        with patch.dict(os.environ, env, clear=True):
            cfg = load_config()

        self.assertTrue(cfg["translation"]["enabled"])
        self.assertEqual(cfg["translation"]["target_language"], "en")

    def test_azure_provider_requires_api_key_and_url(self) -> None:
        config_path = self._write_config(
            BASE_CONFIG
            + """
[translation]
  enabled = true
  target_language = "en"
  provider = "azure"
"""
        )
        env = self._clean_env()
        env["WEIBO_CONFIG_FILE"] = config_path

        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                load_config()

    def test_azure_provider_accepts_valid_credentials(self) -> None:
        config_path = self._write_config(
            BASE_CONFIG
            + """
[translation]
  enabled = true
  target_language = "en"
  provider = "azure"
  api_key = "key-123"
  api_url = "https://example.cognitiveservices.azure.com/"
  region = "eastus"
"""
        )
        env = self._clean_env()
        env["WEIBO_CONFIG_FILE"] = config_path

        with patch.dict(os.environ, env, clear=True):
            cfg = load_config()

        self.assertEqual(cfg["translation"]["provider"], "azure")
        self.assertEqual(cfg["translation"]["api_key"], "key-123")
        self.assertEqual(cfg["translation"]["api_url"], "https://example.cognitiveservices.azure.com/")
        self.assertEqual(cfg["translation"]["region"], "eastus")


if __name__ == "__main__":
    unittest.main()

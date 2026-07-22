from __future__ import annotations

import types
import unittest
from unittest.mock import patch

from services.translator import TranslationService


class _DetectResult:
    def __init__(self, lang: str):
        self.lang = lang


class _TranslateResult:
    def __init__(self, text: str):
        self.text = text


class _FakeTranslator:
    detect_lang = "zh-cn"
    translated_text = "Hello world"
    fail_detect = False
    fail_translate = False

    def __init__(self, timeout: int = 8):
        self.timeout = timeout

    def detect(self, text: str):
        if self.fail_detect:
            raise RuntimeError("detect failed")
        return _DetectResult(self.detect_lang)

    def translate(self, text: str, dest: str):
        if self.fail_translate:
            raise RuntimeError("translate failed")
        return _TranslateResult(self.translated_text)


class _FakeAsyncTranslator:
    detect_lang = "zh"
    translated_text = "Hello"

    def __init__(self, timeout: int = 8):
        self.timeout = timeout

    async def detect(self, text: str):
        return _DetectResult(self.detect_lang)

    async def translate(self, text: str, dest: str):
        return _TranslateResult(self.translated_text)


class _FakeAsyncFailTranslator:
    def __init__(self, timeout: int = 8):
        self.timeout = timeout

    async def detect(self, text: str):
        raise RuntimeError("upstream runtime error")

    async def translate(self, text: str, dest: str):
        return _TranslateResult("unused")


class TranslationServiceTests(unittest.TestCase):
    def _patch_googletrans(self):
        fake_module = types.SimpleNamespace(Translator=_FakeTranslator)
        return patch.dict("sys.modules", {"googletrans": fake_module})

    def test_renders_original_and_translated_sections(self) -> None:
        _FakeTranslator.detect_lang = "zh-cn"
        _FakeTranslator.translated_text = "Hello world"
        _FakeTranslator.fail_detect = False
        _FakeTranslator.fail_translate = False

        with self._patch_googletrans():
            service = TranslationService({"enabled": True, "target_language": "en", "provider": "googletrans"})
            rendered = service.render_body("你好世界")

        self.assertEqual(rendered, "你好世界\n---\nHello world")

    def test_source_equals_target_returns_original_only(self) -> None:
        _FakeTranslator.detect_lang = "en"
        _FakeTranslator.translated_text = "Hello world"
        _FakeTranslator.fail_detect = False
        _FakeTranslator.fail_translate = False

        with self._patch_googletrans():
            service = TranslationService({"enabled": True, "target_language": "en", "provider": "googletrans"})
            rendered = service.render_body("Hello world")

        self.assertEqual(rendered, "Hello world")

    def test_translate_failure_returns_original_only(self) -> None:
        _FakeTranslator.detect_lang = "zh"
        _FakeTranslator.translated_text = ""
        _FakeTranslator.fail_detect = False
        _FakeTranslator.fail_translate = True

        with self._patch_googletrans():
            service = TranslationService({"enabled": True, "target_language": "en", "provider": "googletrans"})
            rendered = service.render_body("你好")

        self.assertEqual(rendered, "你好")

    def test_async_translator_methods_are_supported(self) -> None:
        fake_module = types.SimpleNamespace(Translator=_FakeAsyncTranslator)
        with patch.dict("sys.modules", {"googletrans": fake_module}):
            service = TranslationService({"enabled": True, "target_language": "en", "provider": "googletrans"})
            rendered = service.render_body("你好")

        self.assertEqual(rendered, "你好\n---\nHello")

    def test_async_runtime_error_falls_back_to_original_text(self) -> None:
        fake_module = types.SimpleNamespace(Translator=_FakeAsyncFailTranslator)
        with patch.dict("sys.modules", {"googletrans": fake_module}):
            service = TranslationService({"enabled": True, "target_language": "en", "provider": "googletrans"})
            rendered = service.render_body("你好")

        self.assertEqual(rendered, "你好")

    def test_async_translator_can_be_reused_for_multiple_calls(self) -> None:
        fake_module = types.SimpleNamespace(Translator=_FakeAsyncTranslator)
        with patch.dict("sys.modules", {"googletrans": fake_module}):
            service = TranslationService({"enabled": True, "target_language": "en", "provider": "googletrans"})
            first = service.render_body("你好")
            second = service.render_body("世界")

        self.assertEqual(first, "你好\n---\nHello")
        self.assertEqual(second, "世界\n---\nHello")


if __name__ == "__main__":
    unittest.main()

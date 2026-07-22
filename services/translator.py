from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


def _normalize_language_code(language: str) -> str:
    value = (language or "").strip().lower().replace("_", "-")
    if not value:
        return ""
    if "-" in value:
        return value.split("-", 1)[0]
    return value


class TranslationService:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.enabled = bool(cfg.get("enabled", False))
        self.provider = str(cfg.get("provider", "googletrans") or "googletrans").strip().lower()
        self.target_language = _normalize_language_code(str(cfg.get("target_language", "") or ""))
        self.timeout_seconds = int(cfg.get("timeout_seconds", 8) or 8)

        self._client: Any = None
        self._provider_available = False
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None

        if not self.enabled:
            return

        if not self.target_language:
            logger.warning("Translation enabled but target language is empty; translation will be skipped")
            self.enabled = False
            return

        self._initialize_provider()

    def _initialize_provider(self) -> None:
        if self.provider != "googletrans":
            logger.warning("Unsupported translation provider '%s'; translation disabled", self.provider)
            self.enabled = False
            return

        try:
            from googletrans import Translator  # type: ignore

            self._client = Translator(timeout=self.timeout_seconds)
            self._provider_available = True
        except Exception as exc:
            logger.warning("Failed to initialize translation provider '%s': %s", self.provider, exc)
            self._provider_available = False

    def _resolve_maybe_awaitable(self, value: Any) -> Any:
        if not inspect.isawaitable(value):
            return value

        if self._async_loop is None or self._async_loop.is_closed():
            self._async_loop = asyncio.new_event_loop()

        return self._async_loop.run_until_complete(value)

    def close(self) -> None:
        if self._async_loop is not None and not self._async_loop.is_closed():
            self._async_loop.close()

    def render_body(self, source_text: str) -> str:
        text = (source_text or "").strip()
        if not text or not self.enabled or not self._provider_available:
            return source_text or ""

        try:
            detected_raw = ""
            detected = self._resolve_maybe_awaitable(self._client.detect(text))
            detected_raw = str(getattr(detected, "lang", "") or "")

            source_lang = _normalize_language_code(detected_raw)
            target_lang = _normalize_language_code(self.target_language)

            if source_lang and target_lang and source_lang == target_lang:
                return source_text

            translated = self._resolve_maybe_awaitable(self._client.translate(text, dest=self.target_language))
            translated_text = str(getattr(translated, "text", "") or "").strip()

            # Failsafe: keep posting the original if translation is empty/unusable.
            if not translated_text:
                return source_text
            if translated_text == text:
                return source_text

            return f"{source_text}\n---\n{translated_text}"
        except Exception as exc:
            # Failsafe requirement: translation problems must never block webhook posts.
            logger.warning("Translation failed, sending original text only: %s", exc)
            return source_text

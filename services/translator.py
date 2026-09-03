from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Dict, Optional

import requests


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
        self.api_key = str(cfg.get("api_key", "") or "").strip()
        self.api_url = str(cfg.get("api_url", "") or "").strip()
        self.region = str(cfg.get("region", "") or "").strip()
        self.api_version = str(cfg.get("api_version", "3.0") or "3.0").strip()

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
        if self.provider == "googletrans":
            try:
                from googletrans import Translator  # type: ignore

                self._client = Translator(timeout=self.timeout_seconds)
                self._provider_available = True
            except Exception as exc:
                logger.warning("Failed to initialize translation provider '%s': %s", self.provider, exc)
                self._provider_available = False
            return

        if self.provider == "azure":
            if not self.api_key or not self.api_url:
                logger.warning(
                    "Azure translation provider requires api_key and api_url; translation disabled"
                )
                self.enabled = False
                return

            # Azure REST API uses the subscription key and optional region header.
            self._provider_available = True
            return

        logger.warning("Unsupported translation provider '%s'; translation disabled", self.provider)
        self.enabled = False

    def _translate_azure(self, text: str) -> str:
        try:
            base = self.api_url.rstrip("/")
            if "/translator/text/" in base:
                translate_url = f"{base}/translate"
            else:
                translate_url = f"{base}/translator/text/v{self.api_version}/translate"

            params = {
                "api-version": self.api_version,
                "to": self.target_language,
            }
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/json",
            }
            if self.region:
                headers["Ocp-Apim-Subscription-Region"] = self.region

            resp = requests.post(
                translate_url,
                params=params,
                headers=headers,
                json=[{"text": text}],
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            response = resp.json()
            if not response:
                return ""

            payload = response[0] if isinstance(response, list) else {}
            translations = payload.get("translations", []) if isinstance(payload, dict) else []
            for item in translations:
                translated_text = item.get("text", "") if isinstance(item, dict) else ""
                if translated_text:
                    return str(translated_text).strip()

            detected = payload.get("detectedLanguage") if isinstance(payload, dict) else None
            if isinstance(detected, dict):
                language = str(detected.get("language", "") or "")
                if language and _normalize_language_code(language) == _normalize_language_code(self.target_language):
                    return ""

            return ""
        except requests.RequestException as exc:
            logger.warning("Azure translation failed: %s", exc)
            return ""
        except Exception as exc:
            logger.warning("Azure translation failed: %s", exc)
            return ""

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
            if self.provider == "azure":
                translated_text = self._translate_azure(text)
                if not translated_text:
                    return source_text
                if translated_text == text:
                    return source_text
                return f"{source_text}\n---\n{translated_text}"

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

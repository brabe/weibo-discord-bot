from __future__ import annotations

import os
import re
import logging
from typing import Dict, Any

import toml


logger = logging.getLogger(__name__)


def _normalize_env_key(value: str) -> str:
    return re.sub(r'[^A-Z0-9]+', '_', value.strip().upper()).strip('_')


def _coerce_bool(value: str) -> bool:
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_weibo_from_env() -> Dict[str, Any]:
    accounts_raw = os.getenv('WEIBO_ACCOUNTS', '').strip()
    accounts: list[str] = [account.strip() for account in accounts_raw.split(',') if account.strip()]

    config: Dict[str, Any] = {'weibo': {}, 'status': {}, 'translation': {}}

    for account_name in accounts:
        env_prefix = f'WEIBO_{_normalize_env_key(account_name)}_'
        account_config: Dict[str, Any] = {}

        for field in ('READ_LINK_URL', 'MESSAGE_WEBHOOK', 'AVATAR_URL', 'TITLE'):
            value = os.getenv(f'{env_prefix}{field}')
            if value is not None and value != '':
                account_config[field.lower()] = value

        config['weibo'][account_name] = account_config

    status_webhook = os.getenv('WEIBO_STATUS_MESSAGE_WEBHOOK')
    if status_webhook:
        config['status']['message_webhook'] = status_webhook

    status_enabled = os.getenv('WEIBO_STATUS_ENABLED')
    if status_enabled is not None and status_enabled.strip() != '':
        config['status']['enabled'] = _coerce_bool(status_enabled)

    translation_enabled = os.getenv('WEIBO_TRANSLATION_ENABLED')
    if translation_enabled is not None and translation_enabled.strip() != '':
        config['translation']['enabled'] = _coerce_bool(translation_enabled)

    translation_target_language = os.getenv('WEIBO_TRANSLATION_TARGET_LANGUAGE')
    if translation_target_language is not None and translation_target_language.strip() != '':
        config['translation']['target_language'] = translation_target_language.strip()

    translation_provider = os.getenv('WEIBO_TRANSLATION_PROVIDER')
    if translation_provider is not None and translation_provider.strip() != '':
        config['translation']['provider'] = translation_provider.strip()

    translation_timeout_seconds = os.getenv('WEIBO_TRANSLATION_TIMEOUT_SECONDS')
    if translation_timeout_seconds is not None and translation_timeout_seconds.strip() != '':
        config['translation']['timeout_seconds'] = _coerce_int(translation_timeout_seconds, 8)

    translation_api_url = os.getenv('WEIBO_TRANSLATION_API_URL')
    if translation_api_url is not None and translation_api_url.strip() != '':
        config['translation']['api_url'] = translation_api_url.strip()

    translation_api_key = os.getenv('WEIBO_TRANSLATION_API_KEY')
    if translation_api_key is not None and translation_api_key.strip() != '':
        config['translation']['api_key'] = translation_api_key.strip()

    translation_region = os.getenv('WEIBO_TRANSLATION_REGION')
    if translation_region is not None and translation_region.strip() != '':
        config['translation']['region'] = translation_region.strip()

    return config


def _merge_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    env_config = _load_weibo_from_env()

    if env_config['weibo']:
        config.setdefault('weibo', {})
        config['weibo'].update(env_config['weibo'])

    if env_config['status']:
        config.setdefault('status', {})
        config['status'].update(env_config['status'])

    if env_config['translation']:
        config.setdefault('translation', {})
        config['translation'].update(env_config['translation'])

    return config


def load_config() -> Dict[str, Any]:
    try:
        config_path = os.getenv('WEIBO_CONFIG_FILE', 'config.toml')
        config: Dict[str, Any] = {}

        if os.path.exists(config_path):
            config = toml.load(config_path)
        else:
            logger.info(f"Config file not found at {config_path}; using environment variables only where provided")

        config = _merge_env_overrides(config)

        status_config = config.setdefault('status', {})
        status_enabled = status_config.get('enabled', True)
        if isinstance(status_enabled, str):
            status_enabled = _coerce_bool(status_enabled)
        status_config['enabled'] = bool(status_enabled)

        translation_config = config.setdefault('translation', {})
        translation_enabled = translation_config.get('enabled', False)
        if isinstance(translation_enabled, str):
            translation_enabled = _coerce_bool(translation_enabled)
        translation_config['enabled'] = bool(translation_enabled)
        translation_config['provider'] = str(translation_config.get('provider', 'googletrans') or 'googletrans').strip().lower()
        if translation_config['provider'] not in {'googletrans', 'azure'}:
            raise ValueError(f"Unsupported translation provider '{translation_config['provider']}'")
        translation_config['timeout_seconds'] = _coerce_int(translation_config.get('timeout_seconds', 8), 8)
        translation_config['api_url'] = str(translation_config.get('api_url', '') or '').strip()
        translation_config['api_key'] = str(translation_config.get('api_key', '') or '').strip()
        translation_config['region'] = str(translation_config.get('region', '') or '').strip()

        target_language = str(translation_config.get('target_language', '') or '').strip().lower()
        if translation_config['enabled'] and not target_language:
            raise ValueError("Missing translation target_language when translation is enabled")
        translation_config['target_language'] = target_language

        if translation_config['enabled'] and translation_config['provider'] == 'azure':
            if not translation_config['api_key']:
                raise ValueError("Missing translation api_key when Azure translation is enabled")
            if not translation_config['api_url']:
                raise ValueError("Missing translation api_url when Azure translation is enabled")
            if not translation_config['region']:
                translation_config['region'] = 'global'

        if 'weibo' not in config:
            raise ValueError("Missing 'weibo' section in configuration")

        if not config['weibo']:
            raise ValueError("No Weibo accounts configured")

        for account_name, account_config in config['weibo'].items():
            if not isinstance(account_config, dict):
                raise ValueError(f"Invalid configuration for account {account_name}")
            if 'read_link_url' not in account_config:
                raise ValueError(f"Missing read_link_url for account {account_name}")
            if 'message_webhook' not in account_config:
                raise ValueError(f"Missing message_webhook for account {account_name}")
            webhook_url = account_config['message_webhook']
            if not webhook_url.startswith('https://discord.com/api/webhooks/'):
                raise ValueError(f"Invalid Discord webhook URL for account {account_name}")

            if 'avatar_url' not in account_config:
                account_config['avatar_url'] = ''
            if 'title' not in account_config:
                account_config['title'] = account_name

        if config['status']['enabled']:
            if 'message_webhook' not in config['status']:
                raise ValueError("Missing status message_webhook in configuration")
            if not config['status']['message_webhook'].startswith('https://discord.com/api/webhooks/'):
                raise ValueError("Invalid Discord status webhook URL")
        else:
            config['status'].pop('message_webhook', None)

        if os.getenv('WEIBO_REQUIRE_TOML', '').strip():
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Required config file not found: {config_path}")

        return config
    except FileNotFoundError:
        logger.error("Error: config file not found. Please create it or provide environment variables.")
        raise
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise



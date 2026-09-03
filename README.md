# Weibo-Discord-Bot

*Read this in other languages: [简体中文](README.zh-CN.md)*

This project is a Python-based bot that scans specified Weibo accounts and sends new posts to designated Discord channels. It's a great tool if you want to keep track of certain Weibo accounts and have updates delivered directly to your Discord server.

## 🚀 Features

* **Multi-Account Monitoring**: Scans multiple Weibo accounts for new posts at scheduled intervals
* **Rich Content Support**: Handles different types of Weibo posts including:
  * Text-only posts
  * Posts with images (single or multiple)
  * Posts with video content
  * Posts with retweeted content
* **Smart Image Processing**: 
  * Creates collages for multiple images
  * Sends GIFs separately for better Discord compatibility
  * Automatic image compression and resizing (max 1024x1024)
  * Aggressive compression to stay under Discord's 8MB limit
* **Duplicate Prevention**: Stores processed post IDs in SQLite database
* **Status Monitoring**: Sends status updates every 6 hours to confirm bot is running
* **Cross-Platform Support**: Works on Windows, macOS, and Linux
* **Automatic Driver Management**: ChromeDriver/GeckoDriver automatically downloaded and managed
* **Enterprise Security**: Comprehensive security features and input validation
* **Rate Limiting**: Built-in rate limiting to prevent API abuse
* **Comprehensive Logging**: Detailed logging with file rotation and monitoring
* **In-browser AJAX capture**: JSON is fetched inside Selenium; no manual AJAX URL required
* **Optional mobile DOM extractor**: Change in code via `core/settings.py` → `EXTRACTION_METHOD`

## 🛡️ Security Features

* **Input Validation**: URL validation against whitelist, file extension validation
* **Rate Limiting**: Maximum 5 requests per minute to prevent API abuse
* **File Security**: Size limits, content type validation, safe file operations
* **Database Security**: SQL injection prevention, connection timeouts, automatic cleanup
* **WebDriver Security**: Headless mode, anti-detection measures, security flags
* **Logging & Monitoring**: Structured logging, error tracking, no sensitive data exposure

## 🔄 Workflow

1. **Content Retrieval**: Bot retrieves content from Weibo AJAX endpoints
2. **Duplicate Check**: Checks if post ID exists in SQLite database
3. **Content Processing**: 
   - **Retweets**: Sends retweeted content to Discord
   - **Images**: Downloads, compresses, and creates collages if needed
   - **Videos**: Sends video links to Discord
   - **Text**: Sends text-only posts
4. **Database Update**: Records new post IDs to prevent duplicates
5. **Status Updates**: Sends periodic status updates to confirm bot operation

## 📋 Requirements

* Python 3.7 or above
* Chrome or Firefox browser (for web scraping)
* Internet connection (for automatic driver download)

## 🚀 Quick Start

```bash
git clone https://github.com/uiharu-kazari/weibo-discord-bot.git
cd weibo-discord-bot
pip install -r requirements.txt
cp config.toml.example config.toml
# Edit config.toml minimally, then run:
python app.py
```

## ⚙️ Configuration

1. **Copy and edit configuration**
   ```bash
   cp config.toml.example config.toml
   ```

2. **Edit `config.toml` with your settings**
   ```toml
   [weibo]
       [weibo.your_account_name]
           read_link_url = "https://weibo.com/u/YOUR_UID"
           message_webhook = "YOUR_DISCORD_WEBHOOK_URL"
           avatar_url = "OPTIONAL_AVATAR_URL"
           title = "Your Account Title"
   
   [status]
       message_webhook = "YOUR_STATUS_WEBHOOK_URL"

      [translation]
         enabled = false
         target_language = "en"
      provider = "googletrans"  # or "azure"
      timeout_seconds = 8
      # When using Azure Translator:
      # api_key = "YOUR_AZURE_KEY"
      # api_url = "https://YOUR_RESOURCE.cognitiveservices.azure.com/"
      # region = "eastus"

### Runtime environment variables

You can also provide the same configuration at runtime with environment variables.

- `WEIBO_CONFIG_FILE` sets an alternate TOML file path.
- `WEIBO_ACCOUNTS` is a comma-separated list of account names to load from env.
- For each account name, use `WEIBO_<ACCOUNT>_READ_LINK_URL`, `WEIBO_<ACCOUNT>_MESSAGE_WEBHOOK`, `WEIBO_<ACCOUNT>_AVATAR_URL`, and `WEIBO_<ACCOUNT>_TITLE`.
- Set `WEIBO_STATUS_ENABLED=false` to disable status messages entirely.
- Use `WEIBO_STATUS_MESSAGE_WEBHOOK` for the status channel webhook.
- Set `WEIBO_TRANSLATION_ENABLED=true` to enable translation.
- Use `WEIBO_TRANSLATION_TARGET_LANGUAGE` for destination language (for example `en`, `ja`, `ko`).
- Optional: `WEIBO_TRANSLATION_PROVIDER` (`googletrans` or `azure`), `WEIBO_TRANSLATION_TIMEOUT_SECONDS`, `WEIBO_TRANSLATION_API_KEY`, `WEIBO_TRANSLATION_API_URL`, and `WEIBO_TRANSLATION_REGION`.

Example:

```bash
WEIBO_ACCOUNTS=genshin_impact \
WEIBO_GENSHIN_IMPACT_READ_LINK_URL=https://weibo.com/u/6593199887 \
WEIBO_GENSHIN_IMPACT_MESSAGE_WEBHOOK=https://discord.com/api/webhooks/... \
WEIBO_GENSHIN_IMPACT_TITLE=Genshin \
WEIBO_TRANSLATION_ENABLED=true \
WEIBO_TRANSLATION_TARGET_LANGUAGE=en \
WEIBO_TRANSLATION_PROVIDER=azure \
WEIBO_TRANSLATION_API_KEY=... \
WEIBO_TRANSLATION_API_URL=https://YOUR_RESOURCE.cognitiveservices.azure.com/ \
WEIBO_TRANSLATION_REGION=eastus \
WEIBO_STATUS_MESSAGE_WEBHOOK=https://discord.com/api/webhooks/... \
python app.py
```

### Translation behavior

- Source language is auto-detected for each post body.
- If source and destination languages are the same, only the original text is posted.
- If translation fails (for example upstream changes), the post is still sent and translation is omitted.

 

## 🎯 Usage

### Basic Usage
```bash
python app.py
```

### Production (optional)
```bash
pm2 start ecosystem.config.js
```

### With Conda Environment
```bash
conda activate web
python app.py
```

## 🔧 Runtime tuning (edit in code)

- Extraction method: `core/settings.py` → `EXTRACTION_METHOD` (`"ajax_json"` default, or `"mobile_dom"`)
- Rate limiting: `core/settings.py` → `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_TIME_WINDOW`
- Timeouts and sizes: `core/settings.py` → `REQUEST_TIMEOUT_SECONDS`, `IMAGE_MAX_DOWNLOAD_BYTES`, `DISCORD_ATTACHMENT_MAX_MB`
- AJAX timing: `core/settings.py` → `AJAX_WAIT_MS`

## 📊 Monitoring & Logging

The bot provides comprehensive logging:
- **File Logging**: `weibo_bot.log` with automatic rotation
- **Console Output**: Real-time status updates
- **Error Tracking**: Detailed error logging with stack traces
- **Performance Monitoring**: Database cleanup, memory usage tracking

### Log Levels
- `DEBUG`: Detailed debugging information
- `INFO`: General operational information
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages with full context

> Note: The bot performs the AJAX request inside the browser session automatically, so you don't need to collect or provide the AJAX URL.

 

> Temporary JSON captures are saved under `weibo_tmp/` and can be safely deleted anytime. Database is stored at `data/weibo.db`.

 

 

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

 

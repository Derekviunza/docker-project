# Scrapy settings for ecommerce_scraper project

BOT_NAME = "ecommerce_scraper"

SPIDER_MODULES = ["ecommerce_scraper.spiders"]
NEWSPIDER_MODULE = "ecommerce_scraper.spiders"

ROBOTSTXT_OBEY = False

# Reasonable default UA (some sites block the default Scrapy UA)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Default request headers (helps with basic WAF/bot filters)
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

# Allow spiders to handle common bot-block status codes (e.g. 403/503) gracefully.
# Individual spiders can still override via `custom_settings` or request meta.
HTTPERROR_ALLOWED_CODES = [403, 404, 429, 503]

LOG_LEVEL = "INFO"

CONCURRENT_REQUESTS = 8
DOWNLOAD_TIMEOUT = 90

# --- Playwright integration (enabled for JS-heavy sites like Masoko) ---
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Required for Scrapy + Playwright
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
}

PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60_000

# IMPORTANT:
# Do NOT add scrapy_playwright.middleware.ScrapyPlaywrightDownloadHandler
# That path does not exist and causes exactly your error.
# DOWNLOADER_MIDDLEWARES = {
#     "scrapy_playwright.middleware.ScrapyPlaywrightMiddleware": 543,
# }

# Let spiders optionally process non-200 responses (e.g., handle 403/503 gracefully)
HTTPERROR_ALLOWED_CODES = [403, 404, 429, 503]

# IMPORTANT:
# Do NOT add scrapy_playwright.middleware.ScrapyPlaywrightDownloadHandler
# That path does not exist and causes exactly your error.
# DOWNLOADER_MIDDLEWARES = {
#     "scrapy_playwright.middleware.ScrapyPlaywrightMiddleware": 543,
# }

# Item pipelines (file output works regardless)
ITEM_PIPELINES = {
    "ecommerce_scraper.pipelines.PostgresPipeline": 300,
}

# Advanced anti-bot settings
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 4
CONCURRENT_REQUESTS_PER_IP = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False  # Set to True to see throttling stats

# Retry settings
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
RETRY_BACKOFF_POLICY = 'exponential'

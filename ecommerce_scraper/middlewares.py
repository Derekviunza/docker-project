import asyncio
import logging
from urllib.parse import urlparse

from playwright.async_api import async_playwright
from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy.http import HtmlResponse
from scrapy.utils.project import get_project_settings


class PlaywrightMiddleware:
    """Downloader middleware that renders selected pages using Playwright.

    Notes:
    - This is a lightweight custom integration. You can also use the official
      scrapy-playwright download handler, but keeping this middleware makes the
      project runnable without refactoring the spiders.
    - Use request.meta['playwright']=True to force Playwright on a request.
    """

    def __init__(self, stats):
        self.stats = stats
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.settings = get_project_settings()
        self.logger = logging.getLogger(__name__)

        # Domains that commonly require JS rendering (can be extended per need)
        self.js_domains = {
            # Assessment targets
            "jumia.co.ke",
            "www.jumia.co.ke",
            "masoko.com",
            "www.masoko.com",
            "phoneplacekenya.com",
            "www.phoneplacekenya.com",
            "laptopclinic.co.ke",
            "www.laptopclinic.co.ke",
        }

    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware instance and register signals."""
        if not crawler.settings.getbool("PLAYWRIGHT_ENABLED", True):
            raise NotConfigured("Playwright not enabled")

        mw = cls(crawler.stats)
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(mw.spider_closed, signal=signals.spider_closed)
        return mw

    async def _init_playwright(self):
        self.playwright = await async_playwright().start()

        launch_options = {
            "headless": self.settings.getbool("PLAYWRIGHT_HEADLESS", True),
            "slow_mo": self.settings.getint("PLAYWRIGHT_SLOW_MO", 0),
        }

        browser_type = self.settings.get("PLAYWRIGHT_BROWSER_TYPE", "chromium")
        if browser_type == "firefox":
            self.browser = await self.playwright.firefox.launch(**launch_options)
        elif browser_type == "webkit":
            self.browser = await self.playwright.webkit.launch(**launch_options)
        else:
            self.browser = await self.playwright.chromium.launch(**launch_options)

        context_options = {
            "viewport": {"width": 1366, "height": 768},
            "ignore_https_errors": self.settings.getbool("PLAYWRIGHT_IGNORE_HTTPS_ERRORS", True),
            "user_agent": self.settings.get("USER_AGENT"),
            "java_script_enabled": True,
        }

        self.context = await self.browser.new_context(**context_options)
        self.context.set_default_timeout(self.settings.getint("PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT", 30000))
        self.page = await self.context.new_page()

    async def spider_opened(self, spider):
        spider.logger.info("Initializing Playwright...")
        await self._init_playwright()

    async def spider_closed(self, spider):
        spider.logger.info("Closing Playwright...")
        try:
            if self.context:
                await self.context.close()
        finally:
            try:
                if self.browser:
                    await self.browser.close()
            finally:
                if self.playwright:
                    await self.playwright.stop()

    def _should_use_playwright(self, request) -> bool:
        if request.meta.get("playwright") is True:
            return True
        domain = urlparse(request.url).netloc.lower()
        return domain in self.js_domains

    async def process_request(self, request, spider):
        """Render the page in Playwright and return an HtmlResponse."""
        if not self._should_use_playwright(request):
            return None

        if not self.page:
            # Safety: if signals didn't fire for some reason
            await self._init_playwright()

        timeout = request.meta.get("playwright_timeout", 30000)
        wait_until = request.meta.get("playwright_wait_until", "domcontentloaded")

        try:
            resp = await self.page.goto(request.url, timeout=timeout, wait_until=wait_until)

            # Optional extra wait for lazy-loaded content
            if request.meta.get("playwright_wait_networkidle"):
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=2000)
                except Exception:
                    pass

            # Optional scroll
            if request.meta.get("scroll_to_bottom"):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(0.7)

            html = await self.page.content()
            final_url = self.page.url
            status = getattr(resp, "status", 200) if resp else 200
            headers = dict(getattr(resp, "headers", {}) or {})

            return HtmlResponse(
                url=final_url,
                status=status,
                headers=headers,
                body=html.encode("utf-8"),
                encoding="utf-8",
                request=request,
            )

        except Exception as e:
            spider.logger.error("Playwright error for %s: %s", request.url, e)
            return HtmlResponse(url=request.url, status=500, body=str(e).encode("utf-8"), request=request)


class RotateUserAgentMiddleware:
    """Simple round-robin User-Agent rotation."""

    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        self._idx = 0

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        if b"User-Agent" in request.headers:
            return
        request.headers[b"User-Agent"] = self.user_agents[self._idx].encode("utf-8")
        self._idx = (self._idx + 1) % len(self.user_agents)


class RetryMiddleware:
    """Lightweight retry middleware placeholder.

    The project settings already enable Scrapy's built-in RetryMiddleware.
    This class exists only because the settings referenced it.
    """

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

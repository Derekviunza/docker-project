import re
import json
import datetime
from urllib.parse import urlparse

import scrapy


class BaseEcommerceSpider(scrapy.Spider):
    """
    Backwards-compatible base spider.

    Some spiders import:
      from .base_spider import BaseEcommerceSpider
    Others import:
      from .base_spider import EcommerceSpider

    So we export BOTH names (EcommerceSpider is an alias below).
    """

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 1.0,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "RETRY_TIMES": 4,
        "RETRY_HTTP_CODES": [429, 500, 502, 503, 504, 408],
    }

    debug_listing: bool = False

    def now_utc_iso(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def norm_space(self, s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip())

    def parse_price(self, text):
        """
        Parse KES/KSh price strings into float.
        Handles: "KSh 116,000", "116000", "116,000.00", etc.
        """
        if text is None:
            return None
        try:
            if isinstance(text, (int, float)):
                return float(text)
            s = str(text).strip()
            if not s:
                return None
            # Remove currency symbols and commas
            s = re.sub(r'[^\d.,]', '', s)
            # Handle thousand separators
            if ',' in s and '.' in s:
                if s.find(',') < s.find('.'):
                    s = s.replace(',', '')
                else:
                    s = s.replace('.', '').replace(',', '.')
            elif ',' in s:
                s = s.replace(',', '.')
            return float(s) if s else None
        except Exception:
            return None

    def safe_float(self, x):
        """Alias for parse_price for backward compatibility"""
        return self.parse_price(x)

    def make_match_key(self, title: str) -> str:
        t = (title or "").lower()
        t = re.sub(r"\(.*?\)", " ", t)
        t = re.sub(r"[^a-z0-9]+", " ", t)
        t = re.sub(r"\b(kenya|nairobi|official|new|latest|sale)\b", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        toks = t.split()[:12]
        return "-".join(toks)

    def extract_jsonld_products(self, response: scrapy.http.Response):
        """
        Return list of Product objects from JSON-LD blocks.
        """
        products = []
        scripts = response.css("script[type='application/ld+json']::text").getall()
        for raw in scripts:
            raw = (raw or "").strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue

            blocks = data if isinstance(data, list) else [data]
            for obj in blocks:
                if not isinstance(obj, dict):
                    continue
                t = obj.get("@type")
                is_product = (t == "Product") or (isinstance(t, list) and "Product" in t)
                if is_product:
                    products.append(obj)
        return products

    def extract_product_jsonld(self, response: scrapy.http.Response):
        """
        Convenience: return (title, price) from first JSON-LD product.
        """
        products = self.extract_jsonld_products(response)
        if not products:
            return None, None

        p = products[0]
        title = self.norm_space(p.get("name") or "")

        offers = p.get("offers")
        price = None
        if isinstance(offers, dict):
            price = offers.get("price") or offers.get("lowPrice") or offers.get("highPrice")
        elif isinstance(offers, list) and offers:
            if isinstance(offers[0], dict):
                price = offers[0].get("price")

        return title or None, self.parse_price(price)

    def log_listing_links(self, response, links, selector_used: str):
        if not getattr(self, "debug_listing", False):
            return
        self.logger.info(
            "Listing page: %s | selector=%s | links_found=%s",
            response.url,
            selector_used,
            len(links),
        )
        if links:
            self.logger.info("Sample links: %s", links[:5])

    def is_same_domain(self, url: str) -> bool:
        try:
            host = urlparse(url).netloc.lower()
            return any(host.endswith(d) for d in (self.allowed_domains or []))
        except Exception:
            return False


# Alias for spiders importing EcommerceSpider
EcommerceSpider = BaseEcommerceSpider

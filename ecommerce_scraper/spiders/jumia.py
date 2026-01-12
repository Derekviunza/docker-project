from urllib.parse import urljoin

import scrapy

from .base_spider import BaseEcommerceSpider


class JumiaSpider(BaseEcommerceSpider):
    name = "jumia"
    allowed_domains = ["jumia.co.ke"]
    start_urls = ["https://www.jumia.co.ke/laptops/"]

    # Jumia listings are JS-heavy
    render_listing_with_playwright = True
    debug_listing = True

    def parse(self, response):
        selector_used = "a.core::attr(href)"
        hrefs = response.css(selector_used).getall()

        # Build absolute URLs, keep likely product URLs (often end with .html)
        links = []
        for h in hrefs:
            if not h:
                continue
            u = urljoin(response.url, h)
            # Jumia product pages typically end with .html, keep those.
            if u.lower().endswith(".html"):
                links.append(u)

        self.log_listing_links(response, links, selector_used)

        for url in links:
            yield scrapy.Request(
                url,
                callback=self.parse_product,
                meta={"playwright": True, "playwright_wait_networkidle": True},
            )

        next_sel = 'a[aria-label="Next Page"]::attr(href)'
        next_page = response.css(next_sel).get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse,
                meta={"playwright": True, "playwright_wait_networkidle": True},
            )

    def parse_product(self, response):
        title = response.css("h1::text").get()

        # Jumia price selector varies; we try a few common ones
        price_raw = (
            response.css("span.-b.-ltr.-tal.-fs24.-prxs::text").get()
            or response.css("span.-b.-ltr.-tal.-fs20.-prxs::text").get()
            or response.css("span.-b::text").get()
        )
        price = self.parse_price(price_raw)

        # JSON-LD fallback
        if not title or price is None:
            jsonld = self.extract_jsonld_products(response)
            if jsonld:
                p = jsonld[0]
                title = title or p.get("name")
                offers = p.get("offers") or {}
                if isinstance(offers, dict):
                    price = price if price is not None else self.parse_price(offers.get("price"))

        item = {
            "source": "jumia",
            "title": (title or "").strip(),
            "price": price,
            "currency": "KES",
            "url": response.url,
            "match_key": self.make_match_key(title or ""),
        }

        # Helpful debug: if still empty, you’ll see what fields were missing
        if self.debug_listing and (not item["title"] or item["price"] is None):
            self.logger.warning("Missing fields on %s | title=%r price_raw=%r", response.url, title, price_raw)

        yield item

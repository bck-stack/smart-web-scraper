"""
Smart Web Scraper with Rotating Proxies
Extracts product/price data from any URL with anti-ban logic.
"""

import asyncio
import csv
import logging
import random
import time
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from playwright.async_api import async_playwright, Browser, Page
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROXY_LIST: list[str] = [
    p.strip() for p in os.getenv("PROXY_LIST", "").split(",") if p.strip()
]

USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "2.0"))
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Product:
    url: str
    name: str
    price: str
    currency: str
    scraped_at: str


# ---------------------------------------------------------------------------
# Proxy rotation
# ---------------------------------------------------------------------------

def get_proxy() -> Optional[dict]:
    """Return a random proxy config dict or None if no proxies configured."""
    if not PROXY_LIST:
        return None
    proxy_url = random.choice(PROXY_LIST)
    return {"server": proxy_url}


# ---------------------------------------------------------------------------
# Core scraper
# ---------------------------------------------------------------------------

class SmartScraper:
    """Async scraper with rotating proxies, random UA, and retry logic."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._browser: Optional[Browser] = None

    async def _launch_browser(self, proxy: Optional[dict]) -> Browser:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=self.headless,
            proxy=proxy,
            args=["--disable-blink-features=AutomationControlled"],
        )
        return browser

    async def _get_page(self, browser: Browser) -> Page:
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
        )
        page = await context.new_page()
        # Hide webdriver fingerprint
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return page

    async def scrape_url(self, url: str) -> Optional[Product]:
        """Scrape a single URL with retry logic and proxy rotation."""
        for attempt in range(1, MAX_RETRIES + 1):
            proxy = get_proxy()
            logger.info("Attempt %d/%d — URL: %s — Proxy: %s", attempt, MAX_RETRIES, url, proxy)
            try:
                browser = await self._launch_browser(proxy)
                page = await self._get_page(browser)

                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

                # Human-like delay
                await asyncio.sleep(random.uniform(1.5, 3.5))

                product = await self._extract_product(page, url)
                await browser.close()
                return product

            except Exception as exc:
                logger.warning("Attempt %d failed: %s", attempt, exc)
                try:
                    await browser.close()
                except Exception:
                    pass
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * attempt)

        logger.error("All %d attempts failed for %s", MAX_RETRIES, url)
        return None

    async def _extract_product(self, page: Page, url: str) -> Product:
        """Extract product data using common CSS selectors (adaptable)."""
        # Generic selectors — override per target site as needed
        name_selectors = [
            "h1.product-title", "h1[itemprop='name']", "h1.title",
            "#productTitle", ".product-name h1", "h1",
        ]
        price_selectors = [
            "[itemprop='price']", ".price", ".product-price",
            "#priceblock_ourprice", ".a-price-whole", ".current-price",
        ]

        name = await self._first_text(page, name_selectors)
        price_raw = await self._first_text(page, price_selectors)

        currency, price = self._parse_price(price_raw)

        return Product(
            url=url,
            name=name,
            price=price,
            currency=currency,
            scraped_at=datetime.utcnow().isoformat(),
        )

    @staticmethod
    async def _first_text(page: Page, selectors: list[str]) -> str:
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    text = (await el.inner_text()).strip()
                    if text:
                        return text
            except Exception:
                continue
        return "N/A"

    @staticmethod
    def _parse_price(raw: str) -> tuple[str, str]:
        """Strip currency symbol and return (currency, amount)."""
        import re
        symbols = {"$": "USD", "€": "EUR", "£": "GBP", "₺": "TRY", "₹": "INR"}
        for sym, code in symbols.items():
            if sym in raw:
                amount = re.sub(r"[^\d.,]", "", raw).strip()
                return code, amount
        amount = re.sub(r"[^\d.,]", "", raw).strip()
        return "N/A", amount or raw


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def save_to_csv(products: list[Product], filename: str = "") -> Path:
    """Save a list of Product records to CSV."""
    if not filename:
        filename = f"products_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    path = OUTPUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[field.name for field in fields(Product)])
        writer.writeheader()
        for p in products:
            writer.writerow(
                {field.name: getattr(p, field.name) for field in fields(Product)}
            )
    logger.info("Saved %d records → %s", len(products), path)
    return path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    urls_env = os.getenv("TARGET_URLS", "")
    urls = [u.strip() for u in urls_env.split(",") if u.strip()]

    if not urls:
        # Demo fallback
        urls = [
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        ]
        logger.info("No TARGET_URLS in .env — using demo URL.")

    scraper = SmartScraper(headless=True)
    results: list[Product] = []

    for url in urls:
        product = await scraper.scrape_url(url)
        if product:
            results.append(product)
            logger.info("Scraped: %s | %s %s", product.name, product.currency, product.price)
        # Polite delay between requests
        await asyncio.sleep(random.uniform(2.0, 5.0))

    if results:
        csv_path = save_to_csv(results)
        print(f"\nDone. {len(results)} products saved to {csv_path}")
    else:
        print("No data extracted.")


if __name__ == "__main__":
    asyncio.run(main())

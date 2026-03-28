# Anti-Ban E-Commerce Scraper

A resilient, production-grade web scraping engine designed to bypass modern anti-bot protections and extract product data at scale flawlessly.

✔ Eliminates IP bans and bot-detection blocks using intelligent proxy and fingerprint rotation
✔ Saves hours of babysitting scripts thanks to robust automatic retry limits and backoff logic
✔ Provides clean, analysis-ready CSV data directly from complex dynamic Javascript-heavy websites

## Use Cases
- **Competitor Intelligence:** Reliably scrape thousands of product prices daily without getting blocked by Cloudflare.
- **Lead Generation:** Securely extract B2B contact information from directories that deploy strict anti-scraping measures.
- **Market Dynamics:** Build massive datasets for AI training or predictive pricing models using continuously harvested web data.

## Project Structure

```
smart-web-scraper/
├── scraper.py          # Main scraper logic
├── requirements.txt
├── .env.example
└── output/             # Generated CSV files (git-ignored)
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Playwright browser
playwright install chromium

# 3. Configure environment
cp .env.example .env
# Edit .env with your proxy list and target URLs
```

## Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `TARGET_URLS` | Comma-separated URLs to scrape | demo URL |
| `PROXY_LIST` | Comma-separated proxy URLs | none |
| `MAX_RETRIES` | Retry attempts per URL | `3` |
| `RETRY_DELAY` | Base delay between retries (seconds) | `2.0` |
| `OUTPUT_DIR` | Output directory for CSV files | `output` |

## Usage

```bash
# Set target URLs in .env, then:
python scraper.py
```

## Example Output

```
2024-05-15 10:23:01 [INFO] Attempt 1/3 — URL: https://example.com/product — Proxy: None
2024-05-15 10:23:04 [INFO] Scraped: A Light in the Attic | GBP 51.77
2024-05-15 10:23:04 [INFO] Saved 1 records → output/products_20240515_102304.csv
```

**CSV output:**
```csv
url,name,price,currency,scraped_at
https://...,A Light in the Attic,51.77,GBP,2024-05-15T10:23:04
```

## Extending

Override `_extract_product()` in `SmartScraper` to add site-specific CSS selectors for any target.

## Tech Stack

`playwright` · `httpx` · `python-dotenv`

## Screenshot

![Preview](screenshots/preview.png)


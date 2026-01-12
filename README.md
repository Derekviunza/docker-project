# E-commerce Data Engineer Technical Test (Laptop Price Comparison)

This project scrapes laptop product listings from **4 Kenyan e-commerce sites**, standardizes messy product titles into a **joinable product_id**, and loads both **raw** and **clean** datasets into Postgres for analytics (e.g., Apache Superset).

The existing Scrapy spiders are kept **as-is** (minimal/no changes) — the workflow is *file-first*: scrape to JSONL, then standardize, then load to DB.

---

## Project layout

```
docker-project/
  ecommerce_scraper/              # Scrapy project (spiders, items, settings)
  scripts/
    standardize_products.py       # Build standardized datasets from JSON/JSONL
    load_to_postgres.py           # Drop/create + ingest raw + cleaned tables
  data/output/                    # Raw and standardized outputs (git-ignored)
  load_data.py                   # Custom script to load JSON data into PostgreSQL
```

---

## 1) Installation (laptop-friendly)

You can run everything locally with Python + Chrome/Chromium.

### Create env and install deps

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r ecommerce_scraper/requirements.txt
playwright install chromium
```

> **Windows note:** Playwright downloads browsers into your user profile. That is normal.

---

## 2) Database Setup

### Start PostgreSQL and Redis

```bash
docker compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)

**Database Credentials:**
- **Database:** `ecommerce_price_comparison`
- **Username:** `ecommerce_user`
- **Password:** `ecommerce_password`

---

## 3) Scrape data (run spiders individually)

**Recent Updates:**
- **Masoko & PhonePlaceKenya spiders** now write data iteratively (like Jumia)
- Removed artificial 40-item limits per page
- Fixed Playwright configuration for JavaScript-heavy sites
- Updated PhonePlaceKenya to use search URL: `https://www.phoneplacekenya.com/?term=laptops&s=&post_type=product&taxonomy=product_cat`

Each spider can be run independently (and therefore in parallel in separate terminals).

```bash
scrapy crawl laptopclinic -O data/output/laptopclinic_full.jsonl -s LOG_LEVEL=INFO
scrapy crawl masoko      -O data/output/masoko_full.jsonl      -s LOG_LEVEL=INFO
scrapy crawl phoneplacekenya -O data/output/phoneplacekenya_full.jsonl -s LOG_LEVEL=INFO
scrapy crawl jumia       -O data/output/jumia_full.jsonl       -s LOG_LEVEL=INFO
```

### Getting “more data”

Avoid `CLOSESPIDER_*` limits for full runs. If you want a quick smoke test:

```bash
scrapy crawl laptopclinic -O data/output/laptopclinic_test.jsonl -s CLOSESPIDER_ITEMCOUNT=20
```

---

## 4) Standardize titles (handles all sources)

This step creates a consistent schema across sources and generates a stable `product_id` for joining.

```bash
python scripts/standardize_products.py \
  --input data/output/laptopclinic_full.jsonl data/output/masoko_full.jsonl data/output/phoneplacekenya_full.jsonl data/output/jumia_full.jsonl \
  --outdir data/output/standardized
```

Outputs:

```
data/output/standardized/laptopclinic.json
data/output/standardized/masoko.json
data/output/standardized/phoneplacekenya.json
data/output/standardized/jumia.json
```

---

## 5) Load data into PostgreSQL

Use the custom loading script to load standardized data into the database:

```bash
python load_data.py
```

This loads **four tables** with the following record counts:
- `jumia` - 1,373 records
- `laptopclinic` - 30 records  
- `masoko` - 94 records
- `phoneplacekenya` - 8 records

---

## 6) Apache Superset Setup

### Start Superset

```bash
mkdir C:\superset
cd C:\superset
curl -L -o docker-compose.yml https://raw.githubusercontent.com/apache/superset/master/docker-compose-non-dev.yml
docker compose up -d
```

### Initialize Superset

```bash
docker exec superset_app superset db upgrade
docker exec superset_app superset fab create-admin --username admin --firstname Admin --lastname User --email admin@example.com --password admin
docker exec superset_app superset init
```

### Access Superset

- **URL:** http://localhost:8088
- **Login:** `admin` / `admin`

---

## 7) Connect Superset to Database

### Add Database Connection

1. In Superset, go to **Settings** → **Database Connections**
2. Click **+ DATABASE**
3. Use this connection string:
   ```
   postgresql+psycopg2://ecommerce_user:ecommerce_password@172.18.0.2:5432/ecommerce_price_comparison
   ```
4. Click **Test Connection** → should succeed
5. Click **Connect**

### Create Price Comparison Dashboard

1. Click **+ DASHBOARD** → **New Dashboard**
2. Name it: `Laptop Price Comparison`
3. Add charts using SQL queries like:

```sql
-- Average price by source
SELECT source, AVG(price) as avg_price, COUNT(*) as product_count
FROM (
  SELECT source, price FROM jumia WHERE price IS NOT NULL
  UNION ALL
  SELECT source, price FROM laptopclinic WHERE price IS NOT NULL
  UNION ALL
  SELECT source, price FROM masoko WHERE price IS NOT NULL
  UNION ALL
  SELECT source, price FROM phoneplacekenya WHERE price IS NOT NULL
) all_data
GROUP BY source
ORDER BY avg_price
```

---

## 8) Project Summary

**Data Sources:**
- **4 Kenyan e-commerce sites:** Jumia, LaptopClinic, Masoko, PhonePlaceKenya
- **Total records:** 1,505 laptop listings

**Technical Stack:**
- **Scrapy** for web scraping with Playwright
- **PostgreSQL** for data storage
- **Apache Superset** for visualization
- **Docker** for containerization

**Key Features:**
- Iterative data writing during scraping
- Standardized product titles and specifications
- Price comparison across multiple sources
- Interactive dashboards for analysis

---

## 9) Recent Updates

**Spider Improvements:**
- **Masoko & PhonePlaceKenya spiders** now write data iteratively (like Jumia)
- Removed artificial 40-item limits per page
- Fixed Playwright configuration for JavaScript-heavy sites
- Updated PhonePlaceKenya to use search URL: `https://www.phoneplacekenya.com/?term=laptops&s=&post_type=product&taxonomy=product_cat`

**Database & Visualization:**
- Complete PostgreSQL setup with Docker
- Automated data loading from JSON to PostgreSQL
- Apache Superset integration for price comparison dashboards
- 4 e-commerce sources: Jumia, LaptopClinic, Masoko, PhonePlaceKenya

---

## 10) Common issues + fixes

### 1) Scrapy fails before running any spider (import errors)

**Fix:** Ensure you're in the `docker-project` directory where `scrapy.cfg` exists.

### 2) Playwright `NotImplementedError` on Windows

**Fix:** Use the provided `settings.py` configuration with proper Playwright handlers.

### 3) Superset connection issues

**Fix:** Use the database IP address instead of `host.docker.internal`:
```
postgresql+psycopg2://ecommerce_user:ecommerce_password@172.18.0.2:5432/ecommerce_price_comparison
```

### 4) Site protection issues (403/503 errors)

If product detail pages return 403, it's a site protection issue (WAF/bot controls). Common mitigations:
* reduce concurrency / increase delay
* set realistic User-Agent + headers
* use Playwright page-level navigation (already used)

---

## 11) Workflow Summary

1. **Setup:** Install dependencies, start PostgreSQL with Docker
2. **Scrape:** Run spiders to collect data from 4 e-commerce sites
3. **Standardize:** Process and normalize product data
4. **Load:** Insert data into PostgreSQL database
5. **Visualize:** Create dashboards in Superset for price analysis

---

## 12) What you can build on top

* Price history snapshots (add `scraped_at`)
* Scheduled scrapes (cron/GitHub Actions)
* Dashboard cards: cheapest by product_id, savings spread, stock availability
* Price trend analysis and alerts
* Cross-site price comparison alerts

---

## 13) Database Connection Summary

**PostgreSQL Connection String:**
```
postgresql+psycopg2://ecommerce_user:ecommerce_password@172.18.0.2:5432/ecommerce_price_comparison
```

**Available Tables:**
- `jumia` (1,373 records)
- `laptopclinic` (30 records)
- `masoko` (94 records)
- `phoneplacekenya` (8 records)

**Superset Access:**
- URL: http://localhost:8088
- Login: admin / admin

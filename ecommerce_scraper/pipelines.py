import os
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


class PostgresPipeline:
    """
    Writes items to Postgres if DATABASE_URL is reachable.
    If DB is not reachable, it auto-disables so FEEDS output still works.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.engine = None
        self.enabled = False

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider):
        """Enable DB writes only when explicitly requested.

        Why: during development you often want to scrape large datasets to
        JSONL first, and only load to Postgres later (so crawls can run in
        parallel and retries don't slow down DB).
        """

        # Opt-in flag to avoid surprises (default: disabled)
        if os.getenv("ENABLE_DB_PIPELINE", "0") not in {"1", "true", "TRUE", "yes", "YES"}:
            self.logger.info("DB pipeline disabled (set ENABLE_DB_PIPELINE=1 to enable).")
            self.enabled = False
            return

        db_url = os.getenv("DATABASE_URL")  # required when enabled
        if not db_url:
            self.logger.warning("ENABLE_DB_PIPELINE=1 but DATABASE_URL not set -> DB pipeline disabled.")
            self.enabled = False
            return

        try:
            self.engine = create_engine(db_url, pool_pre_ping=True)
            table = f"{spider.name}_raw"
            with self.engine.begin() as conn:
                if os.getenv("DROP_CREATE_TABLES", "0") in {"1", "true", "TRUE", "yes", "YES"}:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table};"))

                # Per-spider raw tables (laptopclinic_raw, masoko_raw, phoneplacekenya_raw, ...)
                conn.execute(
                    text(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table} (
                            id SERIAL PRIMARY KEY,
                            source TEXT,
                            title TEXT,
                            price DOUBLE PRECISION,
                            currency TEXT,
                            url TEXT UNIQUE,
                            match_key TEXT,
                            scraped_at TIMESTAMP NULL
                        );
                        """
                    )
                )
            self.enabled = True
            self.logger.info("Connected to Postgres; DB pipeline enabled.")
        except OperationalError as e:
            self.logger.warning("Postgres not reachable -> DB pipeline disabled. Error: %s", e)
            self.enabled = False

    def close_spider(self, spider):
        if self.engine:
            self.engine.dispose()

    def process_item(self, item, spider):
        if not self.enabled:
            return item

        table = f"{spider.name}_raw"

        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        f"""
                        INSERT INTO {table} (source, title, price, currency, url, match_key, scraped_at)
                        VALUES (:source, :title, :price, :currency, :url, :match_key, :scraped_at)
                        ON CONFLICT (url) DO UPDATE SET
                            source=EXCLUDED.source,
                            title=EXCLUDED.title,
                            price=EXCLUDED.price,
                            currency=EXCLUDED.currency,
                            match_key=EXCLUDED.match_key,
                            scraped_at=EXCLUDED.scraped_at
                        """
                    ),
                    {**dict(item), "scraped_at": item.get("scraped_at")},
                )
        except Exception as e:
            self.logger.warning("DB insert failed: %s", e)

        return item

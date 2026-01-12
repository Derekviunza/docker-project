"""Load raw + standardized datasets into Postgres as separate tables.

Tables created (dropped/recreated each run):
  - laptopclinic_raw, masoko_raw, phoneplacekenya_raw
  - laptopclinic_clean, masoko_clean, phoneplacekenya_clean

Duplicates are removed on URL (keep last).

Usage:
  export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/ecommerce"
  python scripts/load_to_postgres.py \
    --raw output/laptopclinic_full.jsonl:... \
    --raw output/masoko_full.jsonl:masoko \
    --raw output/phoneplacekenya_full.jsonl:phoneplacekenya \
    --clean output/standardized/laptopclinic.jsonl:laptopclinic \
    --clean output/standardized/masoko.jsonl:masoko \
    --clean output/standardized/phoneplacekenya.jsonl:phoneplacekenya
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from sqlalchemy import create_engine, text


def iter_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def read_any(path: Path) -> List[Dict]:
    # JSONL
    if path.suffix.lower() in {".jsonl", ".jl"}:
        return list(iter_jsonl(path))
    # JSON
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        return data["items"]
    return [data]


def drop_create_table(conn, table: str, columns_sql: str) -> None:
    conn.execute(text(f"DROP TABLE IF EXISTS {table};"))
    conn.execute(text(f"CREATE TABLE {table} ({columns_sql});"))


def load_df(conn, df: pd.DataFrame, table: str) -> None:
    # pandas to_sql is simple and fast enough for this test.
    df.to_sql(table, conn, if_exists="append", index=False, method="multi", chunksize=2000)


def normalize_raw_df(records: List[Dict], source: str) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records)
    # Ensure expected columns exist
    for col in ["source", "title", "price", "currency", "url", "match_key"]:
        if col not in df.columns:
            df[col] = None
    df["source"] = df["source"].fillna(source)
    # Dedup by url (keep last)
    if "url" in df.columns:
        df = df.dropna(subset=["url"])
        df = df.drop_duplicates(subset=["url"], keep="last")
    return df[["source", "title", "price", "currency", "url", "match_key"]]


def normalize_clean_df(records: List[Dict], source: str) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records)
    for col in [
        "source",
        "title",
        "price",
        "currency",
        "url",
        "match_key",
        "brand",
        "model",
        "cpu_type",
        "ram_gb",
        "storage_gb",
        "screen_size_inches",
        "product_id",
        "normalized_title",
    ]:
        if col not in df.columns:
            df[col] = None

    df["source"] = df["source"].fillna(source)
    if "url" in df.columns:
        df = df.dropna(subset=["url"])
        df = df.drop_duplicates(subset=["url"], keep="last")

    cols = [
        "source",
        "title",
        "price",
        "currency",
        "url",
        "match_key",
        "brand",
        "model",
        "cpu_type",
        "ram_gb",
        "storage_gb",
        "screen_size_inches",
        "product_id",
        "normalized_title",
    ]
    return df[cols]


def parse_pairs(values: List[str]) -> List[Tuple[Path, str]]:
    out: List[Tuple[Path, str]] = []
    for v in values:
        p, src = v.split(":", 1)
        out.append((Path(p), src))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy DB url. If omitted, DATABASE_URL env var is used.",
    )
    ap.add_argument(
        "--raw",
        action="append",
        default=[],
        help="Pair in form path:source (repeatable)",
    )
    ap.add_argument(
        "--clean",
        action="append",
        default=[],
        help="Pair in form path:source (repeatable)",
    )
    args = ap.parse_args()

    db_url = args.database_url
    if not db_url:
        import os

        db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not set (use --database-url or env var)")

    engine = create_engine(db_url, pool_pre_ping=True)
    raw_pairs = parse_pairs(args.raw)
    clean_pairs = parse_pairs(args.clean)

    with engine.begin() as conn:
        for path, src in raw_pairs:
            records = read_any(path)
            df = normalize_raw_df(records, src)
            table = f"{src}_raw"
            drop_create_table(
                conn,
                table,
                """
                id SERIAL PRIMARY KEY,
                source TEXT,
                title TEXT,
                price DOUBLE PRECISION,
                currency TEXT,
                url TEXT,
                match_key TEXT
                """.strip(),
            )
            load_df(conn, df, table)
            conn.execute(text(f"CREATE UNIQUE INDEX {table}_url_uq ON {table}(url);"))
            print(f"✅ Loaded {len(df)} rows -> {table}")

        for path, src in clean_pairs:
            records = read_any(path)
            df = normalize_clean_df(records, src)
            table = f"{src}_clean"
            drop_create_table(
                conn,
                table,
                """
                id SERIAL PRIMARY KEY,
                source TEXT,
                title TEXT,
                price DOUBLE PRECISION,
                currency TEXT,
                url TEXT,
                match_key TEXT,
                brand TEXT,
                model TEXT,
                cpu_type TEXT,
                ram_gb INTEGER,
                storage_gb INTEGER,
                screen_size_inches DOUBLE PRECISION,
                product_id TEXT,
                normalized_title TEXT
                """.strip(),
            )
            load_df(conn, df, table)
            conn.execute(text(f"CREATE UNIQUE INDEX {table}_url_uq ON {table}(url);"))
            print(f"✅ Loaded {len(df)} rows -> {table}")

    engine.dispose()


if __name__ == "__main__":
    main()

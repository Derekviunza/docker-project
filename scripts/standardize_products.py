"""Standardize raw scraped laptop records into a comparison-ready schema.

This script is intentionally *file-first*:
  1) Run spiders to JSONL (parallel-friendly)
  2) Run this standardizer to produce standardized JSONL per source

It is resilient to different input shapes (especially Masoko), handling:
  - JSONL (one JSON object per line)
  - JSON arrays
  - Masoko API-like payloads containing an "items" list
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


BRANDS = {
    "HP": r"\bhp\b|hewlett",
    "DELL": r"\bdell\b",
    "LENOVO": r"\blenovo\b|thinkpad|ideapad|yoga",
    "APPLE": r"\bapple\b|macbook|imac",
    "MICROSOFT": r"\bmicrosoft\b|surface",
    "ASUS": r"\basus\b|zenbook|vivobook|rog",
    "ACER": r"\bacer\b|aspire|predator",
    "SAMSUNG": r"\bsamsung\b|galaxy\s?book",
}


def _first(value: Any, default: Any = "") -> Any:
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default


def iter_records(path: Path) -> Iterator[Dict[str, Any]]:
    """Yield JSON objects from a JSONL file or a JSON array file."""

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return

    # JSON array file
    if text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Last-resort: try to clean trailing commas
            cleaned = re.sub(r",\s*]", "]", text)
            cleaned = re.sub(r",\s*}", "}", cleaned)
            data = json.loads(cleaned)

        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            for rec in data["items"]:
                if isinstance(rec, dict):
                    yield rec
            return

        if isinstance(data, list):
            for rec in data:
                if isinstance(rec, dict):
                    yield rec
            return

        if isinstance(data, dict):
            yield data
        return

    # JSONL file
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Sometimes logs get mixed in; ignore non-JSON lines
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Masoko may produce payload objects with "items".
        if isinstance(obj, dict) and "items" in obj and isinstance(obj["items"], list):
            for rec in obj["items"]:
                if isinstance(rec, dict):
                    yield rec
            continue

        if isinstance(obj, dict):
            yield obj


def extract_brand(title: str) -> str:
    tl = title.lower()
    for brand, pat in BRANDS.items():
        if re.search(pat, tl):
            return brand
    return "UNKNOWN"


def extract_ram_gb(title: str) -> int:
    m = re.search(r"(\d+)\s*(?:gb|g\s*b|gigabytes?)\b", title.lower())
    return int(m.group(1)) if m else 0


def extract_storage_gb(title: str) -> int:
    # Prefer SSD/HDD sizes when present. Handles "512GB", "1TB", etc.
    m = re.search(r"(\d+)\s*(tb|gb)\s*(?:ssd|hdd)?", title.lower())
    if not m:
        return 0
    size = int(m.group(1))
    unit = m.group(2)
    return size * 1024 if unit == "tb" else size


def extract_screen_inches(title: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\"|inch|inches)\b", title.lower())
    return float(m.group(1)) if m else 0.0


def extract_cpu_family(title: str) -> str:
    tl = title.lower()
    if re.search(r"\b(i3|i5|i7|i9)\b", tl) or "intel" in tl or "core" in tl:
        return "INTEL"
    if "ryzen" in tl:
        return "AMD"
    if re.search(r"\bm[1-5]\b", tl) or "apple" in tl:
        return "APPLE"
    return "UNKNOWN"


def build_product_id(brand: str, match_key: str, ram_gb: int, storage_gb: int, screen_in: float) -> str:
    # match_key already collapses most title variation; enrich a little with specs
    base = f"{brand}|{match_key}|{ram_gb}GB|{storage_gb}GB|{screen_in:.1f}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()[:16].upper()


def normalize_record(rec: Dict[str, Any], default_source: str) -> Dict[str, Any]:
    """Normalize various raw shapes into the canonical raw shape."""

    # Preferred fields from our spiders
    source = str(_first(rec.get("source"), default_source) or default_source)
    title = str(_first(rec.get("title"), "") or "")
    url = str(_first(rec.get("url"), "") or "")
    currency = str(_first(rec.get("currency"), "KES") or "KES")

    price_val = _first(rec.get("price"), 0)
    try:
        price = float(price_val)
    except Exception:
        price = 0.0

    match_key = str(_first(rec.get("match_key"), "") or "")

    # If this is a Masoko Magento API record, map a few common fields.
    if not title and "name" in rec:
        title = str(rec.get("name") or "")
    if not price and isinstance(rec.get("price"), dict):
        # Rare: nested price objects
        try:
            price = float(rec["price"].get("value") or 0)
        except Exception:
            price = 0.0
    if not url:
        for k in ("product_url", "url_key", "link"):
            if rec.get(k):
                url = str(rec.get(k))
                break

    if not match_key:
        # last resort: slug-ish key from title
        match_key = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:120]

    return {
        "source": source,
        "title": title,
        "price": price,
        "currency": currency,
        "url": url,
        "match_key": match_key,
        "scraped_at": _first(rec.get("scraped_at"), None),
    }


def standardize(raw: Dict[str, Any]) -> Dict[str, Any]:
    title = raw["title"] or ""

    brand = extract_brand(title)
    ram_gb = extract_ram_gb(title)
    storage_gb = extract_storage_gb(title)
    screen_in = extract_screen_inches(title)
    cpu_family = extract_cpu_family(title)

    product_id = build_product_id(brand, raw["match_key"], ram_gb, storage_gb, screen_in)

    return {
        **raw,
        "brand": brand,
        "cpu_family": cpu_family,
        "ram_gb": ram_gb,
        "storage_gb": storage_gb,
        "screen_size_inches": screen_in,
        "product_id": product_id,
    }


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Raw JSONL/JSON file path")
    ap.add_argument("--source", required=True, help="Source name, e.g. laptopclinic|masoko|phoneplacekenya")
    ap.add_argument(
        "--output",
        default=None,
        help="Output standardized JSONL (default: output/standardized/<source>.jsonl)",
    )
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output) if args.output else Path("output") / "standardized" / f"{args.source}.jsonl"

    raw_records = (normalize_record(r, args.source) for r in iter_records(in_path))
    standardized = (standardize(r) for r in raw_records)
    count = write_jsonl(out_path, standardized)
    print(f"✅ Wrote {count} standardized records -> {out_path}")


if __name__ == "__main__":
    main()

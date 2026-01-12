"""NLP-ish laptop product standardization & primary-key generation.

Reads Scrapy JSONL exports from ./output and produces:
 - output/nlp_standardized_products.json
 - output/nlp_standardized_products.csv
 - output/nlp_comparison_report.json

This script is intentionally deterministic (rule-based extraction + hashing)
so the same product always gets the same primary key across sources.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


OUTPUT_DIR = Path("output")


def read_jsonl(path: Path) -> List[Dict]:
    items: List[Dict] = []
    if not path.exists():
        return items
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def extract_brand(title: str) -> str:
    t = (title or "").lower()
    brands = {
        "HP": r"\bhp\b|hewlett",
        "DELL": r"\bdell\b",
        "LENOVO": r"\blenovo\b|thinkpad|ideapad",
        "APPLE": r"\bapple\b|macbook|imac",
        "MICROSOFT": r"\bmicrosoft\b|surface",
        "ASUS": r"\basus\b|rog|zenbook|vivobook",
        "ACER": r"\bacer\b|aspire|predator",
        "SAMSUNG": r"\bsamsung\b|galaxy\s?book",
        "TOSHIBA": r"\btoshiba\b|portege|satellite",
    }
    for brand, pattern in brands.items():
        if re.search(pattern, t):
            return brand
    return "UNKNOWN"


def extract_ram_gb(title: str) -> int:
    t = (title or "").lower()
    m = re.search(r"(\d{1,2})\s*(?:gb|g\s*b|gigabytes?)\b", t)
    return int(m.group(1)) if m else 0


def extract_screen_inches(title: str) -> float:
    t = (title or "").lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\"|inch|inches)\b", t)
    return float(m.group(1)) if m else 0.0


def extract_cpu_family(title: str) -> str:
    t = (title or "").lower()
    if re.search(r"\bcore\s*i[3579]\b|\bi[3579]-\d+", t):
        return "INTEL_CORE"
    if "ryzen" in t:
        return "AMD_RYZEN"
    if re.search(r"\bm[1234]\b", t) or "apple silicon" in t:
        return "APPLE_SILICON"
    if "celeron" in t:
        return "INTEL_CELERON"
    if "pentium" in t:
        return "INTEL_PENTIUM"
    return "UNKNOWN"


def extract_model_hint(title: str, brand: str) -> str:
    """Best-effort model extraction.

The goal is not perfect parsing, but stable grouping across retailers.
"""
    t = (title or "").lower()

    brand = brand.upper()
    patterns = {
        "HP": [
            r"elitebook\s*([a-z0-9]+)",
            r"probook\s*([a-z0-9]+)",
            r"pavilion\s*([a-z0-9]+)",
            r"envy\s*([a-z0-9]+)",
            r"zbook\s*([a-z0-9]+)",
        ],
        "DELL": [r"latitude\s*([a-z0-9]+)", r"inspiron\s*([a-z0-9]+)", r"xps\s*([a-z0-9]+)"],
        "LENOVO": [r"thinkpad\s*([a-z]+\d+[a-z0-9]*)", r"ideapad\s*([a-z]+\d+[a-z0-9]*)", r"yoga\s*([a-z]+\d+[a-z0-9]*)"],
        "ASUS": [r"zenbook\s*([a-z0-9-]+)", r"vivobook\s*([a-z0-9-]+)", r"rog\s*([a-z0-9-]+)"],
        "APPLE": [r"macbook\s*(air|pro)?\s*(\d+(?:\.\d+)?)?"],
        "MICROSOFT": [r"surface\s*(pro|laptop|go)?\s*(\d+)?"],
    }

    for pat in patterns.get(brand, []):
        m = re.search(pat, t)
        if not m:
            continue
        # Use last non-empty capture group
        for g in reversed(m.groups()):
            if g:
                return re.sub(r"[^a-z0-9]", "", g).upper()
        return re.sub(r"[^a-z0-9]", "", m.group(0)).upper()

    # Fallback: first alphanumeric model-like token
    m2 = re.search(r"\b[a-z]{1,6}\d{2,6}[a-z0-9]{0,4}\b", t)
    return m2.group(0).upper() if m2 else "UNKNOWN"


def normalize_model(brand: str, model: str) -> str:
    brand = brand.upper() if brand else "UNKNOWN"
    model = model.upper() if model else "UNKNOWN"
    return f"{brand} {model}".strip()


def make_primary_key(brand: str, model: str, cpu: str, ram: int, screen: float) -> str:
    parts = [brand.upper(), model.upper(), cpu.upper(), f"{ram}GB"]
    if screen > 0:
        parts.append(f"{screen:g}IN")
    s = "_".join(parts)
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:16].upper()


def standardize_item(item: Dict) -> Dict:
    title = item.get("title") or ""
    brand = extract_brand(title)
    cpu = extract_cpu_family(title)
    ram = extract_ram_gb(title)
    screen = extract_screen_inches(title)
    model = extract_model_hint(title, brand)
    normalized_model = normalize_model(brand, model)
    primary_key = make_primary_key(brand, model, cpu, ram, screen)

    price = item.get("price")
    try:
        price = float(price) if price is not None else 0.0
    except Exception:
        price = 0.0

    return {
        "primary_key": primary_key,
        "normalized_model": normalized_model,
        "source": item.get("source", ""),
        "original_title": title,
        "price": price,
        "currency": item.get("currency", ""),
        "url": item.get("url", ""),
        "scraped_at": item.get("scraped_at", ""),
        "brand": brand,
        "model": model,
        "cpu_type": cpu,
        "ram_gb": ram,
        "screen_size_inches": screen,
        "price_per_gb": (price / ram) if ram else 0.0,
        "has_ssd": bool(re.search(r"\bssd\b", title.lower())),
        "is_apple": brand == "APPLE",
        "is_business": bool(re.search(r"elitebook|thinkpad|latitude|probook", title.lower())),
    }


def group_by_primary_key(items: List[Dict]) -> Dict[str, List[Dict]]:
    groups: Dict[str, List[Dict]] = {}
    for it in items:
        groups.setdefault(it["primary_key"], []).append(it)
    # keep only real matches (>=2 sources)
    out = {}
    for pk, lst in groups.items():
        sources = {x.get("source", "") for x in lst}
        if len(lst) > 1 and len(sources) > 1:
            out[pk] = lst
    return out


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Default inputs (JSONL exports). Add/remove as needed.
    inputs = [
        OUTPUT_DIR / "laptopclinic.jsonl",
        OUTPUT_DIR / "masoko.jsonl",
        OUTPUT_DIR / "phoneplacekenya.jsonl",
    ]

    raw: List[Dict] = []
    for p in inputs:
        raw.extend(read_jsonl(p))

    standardized = [standardize_item(i) for i in raw]
    matches = group_by_primary_key(standardized)

    # Save standardized JSON
    (OUTPUT_DIR / "nlp_standardized_products.json").write_text(
        json.dumps(standardized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Save CSV for BI tools
    csv_path = OUTPUT_DIR / "nlp_standardized_products.csv"
    if standardized:
        fieldnames = list(standardized[0].keys())
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(standardized)

    # Save comparison report
    opportunities = []
    for pk, lst in matches.items():
        prices = [x.get("price", 0.0) for x in lst]
        min_p, max_p = min(prices), max(prices)
        opportunities.append(
            {
                "primary_key": pk,
                "normalized_model": lst[0].get("normalized_model"),
                "brand": lst[0].get("brand"),
                "min_price": min_p,
                "max_price": max_p,
                "savings": max_p - min_p,
                "sources": sorted({x.get("source", "") for x in lst}),
                "products": lst,
            }
        )

    opportunities.sort(key=lambda x: x["savings"], reverse=True)

    report = {
        "summary": {
            "total_products": len(standardized),
            "unique_laptops_with_cross_site_matches": len(matches),
            "price_comparison_opportunities": len(opportunities),
            "brands": sorted({x.get("brand", "") for x in standardized}),
        },
        "top_savings": opportunities[:10],
    }
    (OUTPUT_DIR / "nlp_comparison_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("✅ Standardization complete")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

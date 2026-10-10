"""Star schema for app reviews: one fact table and five dimensions.

Tables are Parquet files in outputs/warehouse/<table>.parquet. Surrogate keys are
deterministic hashes of the natural key, so reruns and parallel runs produce the
same ids and new data can be merged without a key lookup. Unknown members use -1.
"""

import hashlib
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

WAREHOUSE_DIR = Path(__file__).resolve().parent.parent / "outputs" / "warehouse"
UNKNOWN_ID = -1

SCHEMAS = {
    "fact_review": pa.schema([
        ("date_id", pa.int64()),
        ("app_id", pa.int64()),
        ("app_version_id", pa.int64()),
        ("os_id", pa.int64()),
        ("market_id", pa.int64()),
        ("review_id", pa.string()),
        ("content_date", pa.date32()),
        ("content_datetime", pa.string()),
        ("content", pa.string()),
        ("rating", pa.int64()),
        ("source", pa.string()),
    ]),
    "dim_date": pa.schema([
        ("date_id", pa.int64()), ("date", pa.date32()), ("year", pa.int64()),
        ("quarter", pa.int64()), ("month", pa.int64()), ("day", pa.int64()),
        ("iso_week", pa.int64()), ("day_of_week", pa.int64()),
    ]),
    "dim_app": pa.schema([
        ("app_id", pa.int64()), ("store", pa.string()), ("store_app_id", pa.string()),
        ("app_name", pa.string()), ("bundle_id", pa.string()), ("developer", pa.string()),
    ]),
    "dim_app_version": pa.schema([
        ("app_version_id", pa.int64()), ("app_id", pa.int64()), ("app_version", pa.string()),
    ]),
    "dim_os": pa.schema([
        ("os_id", pa.int64()), ("os_name", pa.string()),
    ]),
    "dim_market": pa.schema([
        ("market_id", pa.int64()), ("market_code", pa.string()), ("region", pa.string()),
    ]),
}

# Primary keys, used to de-duplicate when new rows are merged into a table.
KEYS = {
    "fact_review": ["review_id"],
    "dim_date": ["date_id"],
    "dim_app": ["app_id"],
    "dim_app_version": ["app_version_id"],
    "dim_os": ["os_id"],
    "dim_market": ["market_id"],
}

# Market regions as used in the BMW sales data (EU / CN / US / RoW).
EU_CODES = {
    "at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr", "de", "gr", "hu", "ie",
    "it", "lv", "lt", "lu", "mt", "nl", "pl", "pt", "ro", "sk", "si", "es", "se",
    # Not EU members, but part of BMW's European sales region.
    "gb", "no", "ch", "is",
}

STORE_OS = {"app_store": "ios", "google_play": "android"}


def surrogate_key(*parts):
    """Stable positive BIGINT from a natural key."""
    raw = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(raw, digest_size=8).digest(), "big") & (2**63 - 1)


def date_id(d):
    return d.year * 10000 + d.month * 100 + d.day


def region_of(market_code):
    code = market_code.lower()
    if code in EU_CODES:
        return "EU"
    return {"cn": "CN", "us": "US"}.get(code, "RoW")


def dim_date_row(d: date):
    iso = d.isocalendar()
    return {"date_id": date_id(d), "date": d, "year": d.year, "quarter": (d.month - 1) // 3 + 1,
            "month": d.month, "day": d.day, "iso_week": iso.week, "day_of_week": iso.weekday}


def build_tables(reviews, apps):
    """Turn normalized reviews into fact and dimension rows.

    reviews: dicts with store, store_app_id, market, review_id, datetime (aware),
             content, rating, app_version (or None).
    apps:    dicts with store, store_app_id, app_name, bundle_id, developer.
    """
    tables = {name: {} for name in SCHEMAS}
    for a in apps:
        aid = surrogate_key(a["store"], a["store_app_id"])
        tables["dim_app"][aid] = {"app_id": aid, **a}

    for r in reviews:
        d = r["datetime"].date()
        app_id = surrogate_key(r["store"], r["store_app_id"])
        os_name = STORE_OS[r["store"]]
        os_id = surrogate_key(os_name)
        market_id = surrogate_key(r["market"])
        version_id = UNKNOWN_ID
        if r["app_version"]:
            version_id = surrogate_key(app_id, r["app_version"])
            tables["dim_app_version"][version_id] = {
                "app_version_id": version_id, "app_id": app_id, "app_version": r["app_version"]}

        tables["dim_date"][date_id(d)] = dim_date_row(d)
        tables["dim_os"][os_id] = {"os_id": os_id, "os_name": os_name}
        tables["dim_market"][market_id] = {
            "market_id": market_id, "market_code": r["market"].upper(), "region": region_of(r["market"])}
        tables["fact_review"][r["review_id"]] = {
            "date_id": date_id(d),
            "app_id": app_id,
            "app_version_id": version_id,
            "os_id": os_id,
            "market_id": market_id,
            "review_id": r["review_id"],
            "content_date": d,
            "content_datetime": r["datetime"].isoformat(),
            "content": r["content"],
            "rating": r["rating"],
            "source": r["store"],
        }
    return {name: list(rows.values()) for name, rows in tables.items()}


def read_table(name):
    path = WAREHOUSE_DIR / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame({f.name: pd.Series(dtype=object) for f in SCHEMAS[name]})
    return pq.read_table(path).to_pandas()


def upsert(name, rows):
    """Merge rows into a table; newer rows win on key conflicts. Returns the new row count."""
    if not rows:
        return len(read_table(name))
    existing = read_table(name)
    merged = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True) if len(existing) else pd.DataFrame(rows)
    merged = merged.drop_duplicates(subset=KEYS[name], keep="last")
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(merged, schema=SCHEMAS[name], preserve_index=False)
    pq.write_table(table, WAREHOUSE_DIR / f"{name}.parquet")
    return table.num_rows

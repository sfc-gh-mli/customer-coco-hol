"""Deterministic synthetic star-schema fixture data; never connects to Snowflake."""
from __future__ import annotations

import csv
import hashlib
import json
import random
import zipfile
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> dict:
    with path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {"file": path.name, "rows": len(rows), "columns": fields,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def generate_data(root: Path, config: dict) -> dict:
    """Write to a new data directory; refuse to overwrite existing data."""
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=False)
    rng = random.Random(config["data_seed"])
    end_day = date.fromisoformat(config["as_of_date"])
    end_exclusive = datetime.combine(end_day + timedelta(days=1), time())
    start = end_exclusive - timedelta(days=550)
    is_ml = config["track"] == "machine-learning"
    customer_count, transaction_count = (500, 50000) if is_ml else (100, 1200)
    categories = config["categories"]
    locations = [{"LOCATION_ID": number, "LOCATION_NAME": f"Synthetic location {number}"}
                 for number in range(1, 6)]
    customers = [{"CUSTOMER_ID": number, "SEGMENT": "PREMIUM" if number % 10 == 0 else "STANDARD",
                  "LOCATION_ID": 1 + (number % 5)} for number in range(1, customer_count + 1)]
    transactions = []
    totals = defaultdict(int)
    months = defaultdict(int)
    total_cents = 0
    for number in range(1, transaction_count + 1):
        customer_id = rng.randint(1, customer_count)
        category = rng.choice(categories)
        stamp = start + timedelta(seconds=rng.randrange(550 * 86400))
        cents = rng.randint(500, 50000) * (3 if customer_id % 10 == 0 else 1)
        status = rng.choices(["COMPLETED", "CANCELED", "REFUNDED"], weights=[90, 5, 5])[0]
        transactions.append({"TRANSACTION_ID": number, "CUSTOMER_ID": customer_id,
                             "TRANSACTION_TIME": stamp.isoformat(sep=" "),
                             "AMOUNT": f"{cents // 100}.{cents % 100:02d}",
                             "PRODUCT_CATEGORY": category,
                             "CHANNEL": rng.choice(["WEB", "MOBILE", "BRANCH"]), "STATUS": status})
        if status == "COMPLETED":
            total_cents += cents
            totals[category] += cents
            months[stamp.strftime("%Y-%m")] += cents
    manifest = {"synthetic": True, "seed": config["data_seed"],
                "start_inclusive": start.isoformat(), "end_exclusive": end_exclusive.isoformat(),
                "files": []}
    for name, rows in [("locations", locations), ("customers", customers), ("transactions", transactions)]:
        manifest["files"].append(write_csv(data_dir / f"{name}.csv", list(rows[0]), rows))
    with zipfile.ZipFile(data_dir / "synthetic-data.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in manifest["files"]:
            info = zipfile.ZipInfo(entry["file"], date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (data_dir / entry["file"]).read_bytes())
    manifest["zip_sha256"] = hashlib.sha256((data_dir / "synthetic-data.zip").read_bytes()).hexdigest()
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    dictionary = {
        "synthetic": True,
        "industry": config["industry"],
        "categories": categories,
        "net_spend": "SUM(AMOUNT) for STATUS = COMPLETED; canceled/refunded rows contribute zero.",
        "tables": {
            "LOCATIONS": {"grain": "one row per synthetic location", "key": "LOCATION_ID"},
            "CUSTOMERS": {"grain": "one row per synthetic customer", "key": "CUSTOMER_ID",
                          "foreign_key": "LOCATION_ID -> LOCATIONS.LOCATION_ID"},
            "TRANSACTIONS": {"grain": "one row per transaction", "key": "TRANSACTION_ID",
                             "foreign_key": "CUSTOMER_ID -> CUSTOMERS.CUSTOMER_ID",
                             "timestamp": "TRANSACTION_TIME, naive UTC-like simulation",
                             "amount": "fixed-point decimal, 2 places; not real customer currency data"}},
        "warning": "Starter data, not a fitted model, deployed monitor, or customer accounting definition."}
    (data_dir / "data-dictionary.json").write_text(json.dumps(dictionary, indent=2) + "\n", encoding="utf-8")
    expected = {"scope": "all generated history", "synthetic": True,
                "row_counts": {entry["file"]: entry["rows"] for entry in manifest["files"]},
                "net_spend_cents": total_cents,
                "category_net_spend_cents": dict(sorted(totals.items())),
                "monthly_net_spend_cents": dict(sorted(months.items())),
                "distinct_customers_in_transactions": len({row["CUSTOMER_ID"] for row in transactions}),
                "live_tests": {"status": "not_run"}}
    (root / "expected-results.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    return manifest

"""Build the yearly CSV splits uploaded to the Unity Catalog volume.

Reads the Kaggle "Logistics Operations Database" from the local kagglehub
cache and writes one CSV per table per year (2022-2024) for the eight fact
tables, plus a single CSV for each of the six dimension tables.

Rows dated outside 2022-2024 (a few hundred 2025-01-01 spillovers from trips
that crossed the year boundary) are dropped.

Usage:
    python loader/build_annual_csvs.py            # writes ./annual_csvs
    python loader/build_annual_csvs.py --out DIR

Requires: kagglehub download of yogape/logistics-operations-database.
"""
from __future__ import annotations

import argparse
import collections
import csv
import os

DATASET = "yogape/logistics-operations-database"

# table -> date column used to split by year
FACT_TABLES = {
    "loads": "load_date",
    "trips": "dispatch_date",
    "delivery_events": "scheduled_datetime",
    "fuel_purchases": "purchase_date",
    "maintenance_records": "maintenance_date",
    "safety_incidents": "incident_date",
    "driver_monthly_metrics": "month",
    "truck_utilization_metrics": "month",
}

DIMENSION_TABLES = [
    "customers",
    "drivers",
    "trucks",
    "trailers",
    "routes",
    "facilities",
]

YEARS = ("2022", "2023", "2024")


def dataset_dir() -> str:
    import kagglehub

    return kagglehub.dataset_download(DATASET)


def split_facts(src_dir: str, out_dir: str) -> dict[str, collections.Counter]:
    stats: dict[str, collections.Counter] = {}
    for table, date_col in FACT_TABLES.items():
        counts: collections.Counter = collections.Counter()
        writers: dict[str, tuple] = {}
        with open(os.path.join(src_dir, f"{table}.csv"), newline="", encoding="utf-8") as fin:
            reader = csv.DictReader(fin)
            fields = reader.fieldnames
            for row in reader:
                year = (row.get(date_col) or "").strip()[:4]
                if year not in YEARS:
                    counts["OUT_OF_RANGE"] += 1
                    continue
                counts[year] += 1
                if year not in writers:
                    fh = open(
                        os.path.join(out_dir, f"{table}_{year}.csv"),
                        "w",
                        newline="",
                        encoding="utf-8",
                    )
                    w = csv.DictWriter(fh, fieldnames=fields)
                    w.writeheader()
                    writers[year] = (fh, w)
                writers[year][1].writerow(row)
        for fh, _ in writers.values():
            fh.close()
        stats[table] = counts
    return stats


def copy_dimensions(src_dir: str, out_dir: str) -> None:
    for table in DIMENSION_TABLES:
        with open(os.path.join(src_dir, f"{table}.csv"), newline="", encoding="utf-8") as fin:
            with open(os.path.join(out_dir, f"{table}.csv"), "w", newline="", encoding="utf-8") as fout:
                fout.write(fin.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="annual_csvs")
    ap.add_argument("--source", default=None, help="override the kagglehub dataset dir")
    args = ap.parse_args()

    src = args.source or dataset_dir()
    os.makedirs(args.out, exist_ok=True)

    stats = split_facts(src, args.out)
    copy_dimensions(src, args.out)

    for table, counts in stats.items():
        detail = ", ".join(f"{y}:{counts[y]}" for y in YEARS)
        dropped = counts["OUT_OF_RANGE"]
        print(f"{table:28} {detail}  dropped_out_of_range={dropped}")


if __name__ == "__main__":
    main()

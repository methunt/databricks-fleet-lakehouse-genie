"""Build showcase.html, a single-file summary page, from real warehouse numbers.

    python scripts/build_showcase.py            # render from scripts/showcase-data.json
    python scripts/build_showcase.py --refresh  # re-query the warehouse first

Every figure in the page is a {{token}} filled from the data file at build time.
A token the data cannot supply fails the build instead of shipping a blank.

--refresh needs the Databricks CLI (DATABRICKS_BIN or `databricks` on PATH) and a
profile (DATABRICKS_PROFILE, default "DEFAULT"). Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "showcase-data.json"
TEMPLATE = HERE / "showcase.template.html"
OUT = HERE.parent / "showcase.html"

# Rows per yearly CSV, as printed by loader/build_annual_csvs.py.
FILE_COUNTS = {
    "driver_monthly_metrics": [1488, 1488, 1488],
    "truck_utilization_metrics": [1104, 1104, 1104],
}


def q(sql: str) -> list[dict]:
    r = subprocess.run(
        [os.environ.get("DATABRICKS_BIN", "databricks"), "experimental", "aitools", "tools", "query", sql,
         "--profile", os.environ.get("DATABRICKS_PROFILE", "DEFAULT"), "--output", "json"],
        capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        sys.exit(f"query failed:\n{sql}\n{r.stdout[:400]}{r.stderr[:400]}")


def refresh() -> dict:
    T = "fleet_pulse.gold.trip_metrics"
    tot = q(f"SELECT MEASURE(`Total Revenue`) rev, MEASURE(`Total Trips`) trips, MEASURE(`Total Miles`) miles, "
            f"MEASURE(`On Time Rate`) otp, MEASURE(`Average MPG`) mpg, MEASURE(`Deliveries Logged`) logged FROM {T}")[0]
    yearly = q(f"SELECT YEAR(`Trip Date`) y, MEASURE(`Total Revenue`) rev FROM {T} GROUP BY ALL ORDER BY y")
    monthly = q(f"SELECT `Trip Month` m, MEASURE(`On Time Rate`) otp, MEASURE(`Average MPG`) mpg FROM {T} GROUP BY ALL ORDER BY m")
    routes = q(f"SELECT Route id, `Origin City` o, `Destination City` d, MEASURE(`Revenue Per Mile`) rpm FROM {T} GROUP BY ALL")
    cust = q(f"SELECT `Customer Name` n, MEASURE(`On Time Rate`) otp FROM {T} GROUP BY ALL")
    drivers = q("SELECT Driver d, MEASURE(`Total Revenue`) rev FROM fleet_pulse.gold.driver_metrics "
                "WHERE Driver <> 'Unassigned' GROUP BY ALL ORDER BY rev DESC LIMIT 8")
    un = q("SELECT MEASURE(`Trips Completed`) trips, MEASURE(`Total Revenue`) rev FROM fleet_pulse.gold.driver_metrics "
           "WHERE Driver = 'Unassigned'")[0]
    trucks = q("SELECT Truck t, MEASURE(`Downtime Hours`) dt, MEASURE(`Maintenance Events`) ev "
               "FROM fleet_pulse.gold.truck_maintenance_metrics WHERE YEAR(Month)=2024 GROUP BY ALL ORDER BY dt DESC LIMIT 1")[0]
    maint = q("SELECT MEASURE(`Maintenance Cost`) cost, MEASURE(`Maintenance Events`) ev "
              "FROM fleet_pulse.gold.truck_maintenance_metrics")[0]
    src = q("SELECT SUM(total_revenue) rev, SUM(trips_completed) trips, AVG(on_time_delivery_rate) otp "
            "FROM fleet_pulse.bronze.driver_monthly_metrics")[0]
    n = float
    return {
        "generated": dt.date.today().isoformat(),
        "totals": {k: n(v) for k, v in tot.items()},
        "yearly": [{"y": int(y["y"]), "rev": n(y["rev"])} for y in yearly],
        "monthly": [{"otp": n(m["otp"]), "mpg": n(m["mpg"])} for m in monthly],
        "routes": [{"id": r["id"], "o": r["o"], "d": r["d"], "rpm": n(r["rpm"])} for r in routes],
        "customers": [{"n": c["n"], "otp": n(c["otp"])} for c in cust],
        "drivers": [{"d": d["d"], "rev": n(d["rev"])} for d in drivers],
        "unassigned": {"trips": n(un["trips"]), "rev": n(un["rev"])},
        "truck": {"t": trucks["t"], "dt": n(trucks["dt"]), "ev": n(trucks["ev"])},
        "maint": {"cost": n(maint["cost"]), "ev": n(maint["ev"])},
        "source": {"rev": n(src["rev"]), "trips": n(src["trips"]), "otp": n(src["otp"])},
        "files": FILE_COUNTS,
        # measured while diagnosing the cross-view join (README, Part 4)
        "joinfix": {"bad_rev": 143439832, "bad_ratio": 0.046, "good_rev": 292719973, "good_ratio": 0.0235},
    }


def money(x: float, digits: int = 1) -> str:
    return f"${x / 1e6:,.{digits}f}M"


def tokens(d: dict) -> dict[str, str]:
    t, y, src, j = d["totals"], d["yearly"], d["source"], d["joinfix"]
    rev, trips = t["rev"], t["trips"]
    rts = sorted(d["routes"], key=lambda r: -r["rpm"])
    best, worst, second = rts[0], rts[-1], rts[1]
    cust = sorted(d["customers"], key=lambda c: c["otp"])
    gap = rev - src["rev"]
    top = d["drivers"][0]
    tr = d["truck"]
    return {
        "rev": money(rev), "trips": f"{trips:,.0f}", "routes": str(len(d["routes"])),
        "otp": f"{t['otp'] * 100:.1f}%", "otp2": f"{t['otp'] * 100:.1f}%", "mpg": f"{t['mpg']:.2f}", "mpg4": f"{t['mpg']:.4f}",
        "logged": f"{t['logged']:,.0f}",
        "y0": str(y[0]["y"]), "y1": str(y[-1]["y"]), "y0_rev": money(y[0]["rev"]), "y1_rev": money(y[-1]["rev"]),
        "y_change": f"{(y[-1]['rev'] / y[0]['rev'] - 1) * 100:+.1f}%".replace("-", "−"),
        "best_pair": f"{best['o']} → {best['d']}", "best_rpm": f"${best['rpm']:.2f}",
        "worst_pair": f"{worst['o']} → {worst['d']}", "worst_rpm": f"${worst['rpm']:.2f}",
        "second_rpm": f"${second['rpm']:.2f}", "spread": f"{best['rpm'] / worst['rpm']:.1f}×",
        "lead_pct": f"{(best['rpm'] / second['rpm'] - 1) * 100:.0f}%",
        "otp_min": f"{min(m['otp'] for m in d['monthly']) * 100:.1f}%", "otp_max": f"{max(m['otp'] for m in d['monthly']) * 100:.1f}%",
        "mpg_band": f"{max(m['mpg'] for m in d['monthly']) - min(m['mpg'] for m in d['monthly']):.3f}",
        "customers": str(len(cust)), "cust_spread": f"{(cust[-1]['otp'] - cust[0]['otp']) * 100:.1f}",
        "best_cust": cust[-1]["n"], "best_cust_otp": f"{cust[-1]['otp'] * 100:.1f}%",
        "worst_cust": cust[0]["n"], "worst_cust_otp": f"{cust[0]['otp'] * 100:.1f}%",
        "truck": tr["t"], "truck_h": f"{tr['dt']:.1f}", "truck_d": f"{tr['dt'] / 24:.1f}", "truck_ev": f"{tr['ev']:.0f}",
        "maint_ev": f"{d['maint']['ev']:,.0f}", "maint_cost": money(d["maint"]["cost"], 2),
        "top_driver": top["d"], "top_driver_rev": money(top["rev"], 2), "top_driver_pct": f"{top['rev'] / rev * 100:.1f}%",
        "top8_pct": f"{sum(x['rev'] for x in d['drivers']) / rev * 100:.1f}%",
        "src_rev": money(src["rev"]), "gap_rev": money(gap), "gap_pct": f"{gap / rev * 100:.1f}%",
        "src_otp": f"{src['otp'] * 100:.1f}%", "src_trips": f"{src['trips']:,.0f}",
        "agg_lo": f"{trips / sum(d['files']['driver_monthly_metrics']):.0f}×",
        "agg_hi": f"{trips / sum(d['files']['truck_utilization_metrics']):.0f}×",
        "unassigned_trips": f"{d['unassigned']['trips']:,.0f}", "unassigned_rev": money(d["unassigned"]["rev"]),
        "unassigned_gap_share": f"{d['unassigned']['rev'] / gap * 100:.0f}%",
        "unexplained": money(gap - d["unassigned"]["rev"]),
        "bad_rev": money(j["bad_rev"]), "bad_lost": f"{(1 - j['bad_rev'] / rev) * 100:.0f}%", "bad_ratio": str(j["bad_ratio"]),
        "good_rev": money(j["good_rev"]), "good_kept": f"{j['good_rev'] / rev * 100:.0f}%", "good_ratio": str(j["good_ratio"]),
        "gen": d["generated"],
        "w_src": f"{src['rev'] / rev * 100:.1f}",
        "w_bad": f"{j['bad_rev'] / rev * 100:.1f}", "w_good": f"{j['good_rev'] / rev * 100:.1f}",
        "w_best": "100", "w_worst": f"{worst['rpm'] / best['rpm'] * 100:.1f}", "w_second": f"{second['rpm'] / best['rpm'] * 100:.1f}",
        "w_bestcust": f"{cust[-1]['otp'] / cust[-1]['otp'] * 100:.0f}", "w_worstcust": f"{cust[0]['otp'] / cust[-1]['otp'] * 100:.1f}",
        "ring": f"{t['otp'] * 100:.1f}",
        "h0": f"{y[0]['rev'] / max(v['rev'] for v in y) * 100:.1f}", "h1": f"{y[1]['rev'] / max(v['rev'] for v in y) * 100:.1f}",
        "h2": f"{y[2]['rev'] / max(v['rev'] for v in y) * 100:.1f}",
        "y_mid": str(y[1]["y"]), "y_mid_rev": money(y[1]["rev"]),
        "n_bronze": "14", "n_files": "30",
    }


def build(d: dict) -> str:
    tok = tokens(d)

    def sub(m: re.Match) -> str:
        if m.group(1) not in tok:
            sys.exit(f"template references unknown token {{{{{m.group(1)}}}}}")
        return tok[m.group(1)]

    return re.sub(r"\{\{(\w+)\}\}", sub, TEMPLATE.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    if a.refresh or not DATA.exists():
        DATA.write_text(json.dumps(refresh(), indent=1), encoding="utf-8")
        print(f"refreshed {DATA.name}")
    OUT.write_text(build(json.loads(DATA.read_text(encoding="utf-8"))), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

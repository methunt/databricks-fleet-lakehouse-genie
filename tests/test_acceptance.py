"""Acceptance checks for the Fleet Pulse workspace.

The expected values are the human-specified spec (AGENTS.md "Verified numbers").
The agent wrote the checks; the numbers are not the agent's to change.

Run:  DATABRICKS_CONFIG_PROFILE=<profile> python tests/test_acceptance.py
(works under pytest too; no extra dependency needed)
"""
import sys

from databricks.connect import DatabricksSession

spark = DatabricksSession.builder.serverless(True).getOrCreate()


def one(sql):
    return spark.sql(sql).first()[0]


def test_row_counts():
    expected = {
        "bronze.loads": 85410,
        "bronze.trips": 85410,
        "bronze.delivery_events": 170743,
        "silver.trip_events": 85410,
        "gold.on_time_delivery": 77202,
    }
    for table, n in expected.items():
        assert one(f"SELECT COUNT(*) FROM fleet_pulse.{table}") == n, table


def test_gold_not_silently_empty():
    # A pipeline update once reported COMPLETED with 0 rows in gold.on_time_delivery.
    for t in ("on_time_delivery", "route_profitability", "fuel_efficiency_trend"):
        assert one(f"SELECT COUNT(*) FROM fleet_pulse.gold.{t}") > 0, t


def test_revenue_and_trips():
    r = spark.sql(
        "SELECT MEASURE(`Total Revenue`) r, MEASURE(`Total Trips`) t "
        "FROM fleet_pulse.gold.trip_metrics"
    ).first()
    assert round(r.r) == 298621429
    assert r.t == 85410


def test_on_time_rate_uses_logged_deliveries():
    # Denominator is 85,333 logged deliveries, not all 85,410 trips.
    assert one("SELECT COUNT(*) FROM fleet_pulse.silver.trip_events "
               "WHERE scheduled_datetime IS NOT NULL") == 85333
    rate = one("SELECT MEASURE(`On Time Rate`) FROM fleet_pulse.gold.trip_metrics")
    assert abs(rate - 0.3327) < 0.0001


def test_mpg_is_ratio_of_sums():
    # Sum(miles)/Sum(gallons) = 6.4477; averaging per-trip MPG gives 6.5015 (wrong).
    mpg = one("SELECT MEASURE(`Average MPG`) FROM fleet_pulse.gold.truck_metrics")
    assert abs(mpg - 6.4477) < 0.0001


def test_unassigned_driver_kept_not_dropped():
    n = one("SELECT COUNT(*) FROM fleet_pulse.silver.trip_events "
            "WHERE driver_id IS NULL OR driver_id = ''")
    assert n == 1714


def test_truck_join_grain_keeps_revenue():
    # Joining truck_metrics to maintenance on Truck ID + Month halves revenue.
    # Entity grain (Truck ID only) must retain ~$292.7M.
    kept = one("""
        SELECT SUM(rev) FROM (
          SELECT `Truck ID` id, MEASURE(`Total Revenue`) rev
          FROM fleet_pulse.gold.truck_metrics GROUP BY ALL) t
        JOIN (SELECT DISTINCT `Truck ID` id
              FROM fleet_pulse.gold.truck_maintenance_metrics GROUP BY ALL) m
        USING (id)""")
    assert kept > 290_000_000, kept


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as e:  # noqa: BLE001
                failed += 1
                print("FAIL", name, "-", repr(e))
    sys.exit(1 if failed else 0)

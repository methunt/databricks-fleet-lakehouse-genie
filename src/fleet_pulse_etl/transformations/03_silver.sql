-- Silver: star-schema fact table joining loads + trips + delivery_events with
-- customer/route/driver/truck dimension context. Liquid clustering keys on
-- load_year (isolates the 3 yearly bronze batches) plus route_id/driver_id
-- (Genie's common filters). optimizeWrite coalesces the small files that 3
-- discrete batches otherwise leave behind. CLUSTER BY and PARTITIONED BY are
-- mutually exclusive in Lakeflow, so year isolation goes through clustering.
--
-- Expectations drop rows with null dates, negative revenue, or orphan FKs
-- before they can pollute gold aggregates.

CREATE OR REFRESH STREAMING TABLE fleet_pulse.silver.trip_events (
  CONSTRAINT valid_load_date EXPECT (load_date IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_revenue EXPECT (revenue >= 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_customer EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW
)
CLUSTER BY (load_year, route_id, driver_id)
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'Star-schema fact: one row per trip, enriched with load/customer/route/driver/truck context and delivery outcome. Clustered by load_year, route_id, and driver_id for Genie filters.'
AS SELECT
  t.trip_id,
  l.load_id,
  YEAR(l.load_date) AS load_year,
  l.load_date,
  t.dispatch_date,
  l.customer_id,
  c.customer_name,
  c.customer_type,
  l.route_id,
  r.origin_city,
  r.origin_state,
  r.destination_city,
  r.destination_state,
  r.typical_distance_miles,
  t.driver_id,
  d.first_name AS driver_first_name,
  d.last_name AS driver_last_name,
  t.truck_id,
  tr.unit_number AS truck_unit_number,
  l.weight_lbs,
  l.revenue,
  l.fuel_surcharge,
  l.accessorial_charges,
  t.actual_distance_miles,
  t.actual_duration_hours,
  t.fuel_gallons_used,
  t.average_mpg,
  t.idle_time_hours,
  de.scheduled_datetime,
  de.actual_datetime,
  de.detention_minutes,
  CASE WHEN de.actual_datetime <= de.scheduled_datetime THEN true ELSE false END AS on_time_flag
FROM STREAM(fleet_pulse.bronze.loads) l
JOIN STREAM(fleet_pulse.bronze.trips) t ON l.load_id = t.load_id
LEFT JOIN fleet_pulse.bronze.customers c ON l.customer_id = c.customer_id
LEFT JOIN fleet_pulse.bronze.routes r ON l.route_id = r.route_id
LEFT JOIN fleet_pulse.bronze.drivers d ON t.driver_id = d.driver_id
LEFT JOIN fleet_pulse.bronze.trucks tr ON t.truck_id = tr.truck_id
LEFT JOIN fleet_pulse.bronze.delivery_events de
  ON t.trip_id = de.trip_id AND de.event_type = 'Delivery';

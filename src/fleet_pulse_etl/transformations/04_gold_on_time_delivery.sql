-- Gold: on-time delivery rate by customer, route, and month. Clustered by
-- customer_id — Genie's most common filter for this metric.
-- Materialized view, not a streaming table: this is a GROUP BY aggregation
-- over the silver streaming table, which requires a batch read.
CREATE OR REFRESH MATERIALIZED VIEW fleet_pulse.gold.on_time_delivery (
  customer_id STRING COMMENT 'Customer the load was booked for.',
  customer_name STRING COMMENT 'Customer display name.',
  route_id STRING COMMENT 'Lane the load traveled.',
  origin_city STRING COMMENT 'Route origin city.',
  destination_city STRING COMMENT 'Route destination city.',
  delivery_month DATE COMMENT 'Calendar month of scheduled delivery (truncated to month start).',
  total_deliveries BIGINT COMMENT 'Count of delivery events in this group.',
  on_time_deliveries BIGINT COMMENT 'Count of deliveries where actual_datetime <= scheduled_datetime.',
  on_time_rate DOUBLE COMMENT 'on_time_deliveries / total_deliveries.',
  avg_detention_minutes DOUBLE COMMENT 'Average detention minutes across deliveries in this group.'
)
CLUSTER BY (customer_id)
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'On-time delivery rate by customer, route, and month. Answers "which customers/routes have the worst on-time performance" and "is on-time rate trending up or down".'
AS SELECT
  customer_id,
  ANY_VALUE(customer_name) AS customer_name,
  route_id,
  ANY_VALUE(origin_city) AS origin_city,
  ANY_VALUE(destination_city) AS destination_city,
  CAST(DATE_TRUNC('MONTH', scheduled_datetime) AS DATE) AS delivery_month,
  COUNT(*) AS total_deliveries,
  SUM(CASE WHEN on_time_flag THEN 1 ELSE 0 END) AS on_time_deliveries,
  SUM(CASE WHEN on_time_flag THEN 1 ELSE 0 END) / COUNT(*) AS on_time_rate,
  AVG(detention_minutes) AS avg_detention_minutes
FROM fleet_pulse.silver.trip_events
WHERE scheduled_datetime IS NOT NULL
GROUP BY customer_id, route_id, DATE_TRUNC('MONTH', scheduled_datetime);

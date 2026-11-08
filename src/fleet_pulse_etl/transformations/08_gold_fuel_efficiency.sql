-- Gold: MPG and fuel cost trend by month and route. Clustered by route_id —
-- consistent with the other route-level gold tables for Genie join patterns.
-- Materialized view, not a streaming table: this is a GROUP BY aggregation
-- over the silver streaming table, which requires a batch read.
CREATE OR REFRESH MATERIALIZED VIEW fleet_pulse.gold.fuel_efficiency_trend (
  route_id STRING COMMENT 'Lane identifier.',
  origin_city STRING COMMENT 'Route origin city.',
  destination_city STRING COMMENT 'Route destination city.',
  trip_month DATE COMMENT 'Calendar month of trip dispatch (truncated to month start).',
  total_trips BIGINT COMMENT 'Count of trips on this route in this month.',
  total_fuel_gallons DOUBLE COMMENT 'Sum of fuel gallons used across trips in this group.',
  average_mpg DOUBLE COMMENT 'Average miles-per-gallon across trips in this group.',
  total_fuel_cost_estimate DOUBLE COMMENT 'Fuel gallons used times a $3.80/gal reference price — directional cost estimate, not actual purchase cost.'
)
CLUSTER BY (route_id)
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'Monthly fuel efficiency (MPG) and estimated fuel cost by route. Answers "is fuel efficiency improving" and "which routes burn the most fuel".'
AS SELECT
  route_id,
  ANY_VALUE(origin_city) AS origin_city,
  ANY_VALUE(destination_city) AS destination_city,
  CAST(DATE_TRUNC('MONTH', dispatch_date) AS DATE) AS trip_month,
  COUNT(*) AS total_trips,
  SUM(fuel_gallons_used) AS total_fuel_gallons,
  AVG(average_mpg) AS average_mpg,
  SUM(fuel_gallons_used) * 3.80 AS total_fuel_cost_estimate
FROM fleet_pulse.silver.trip_events
GROUP BY route_id, DATE_TRUNC('MONTH', dispatch_date);

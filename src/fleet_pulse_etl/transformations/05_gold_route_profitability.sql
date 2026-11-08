-- Gold: revenue vs. fuel cost by lane and month. Clustered by route_id —
-- Genie's most common filter for profitability questions.
-- Materialized view, not a streaming table: this is a GROUP BY aggregation
-- over the silver streaming table, which requires a batch read.
CREATE OR REFRESH MATERIALIZED VIEW fleet_pulse.gold.route_profitability (
  route_id STRING COMMENT 'Lane identifier.',
  origin_city STRING COMMENT 'Route origin city.',
  origin_state STRING COMMENT 'Route origin state.',
  destination_city STRING COMMENT 'Route destination city.',
  destination_state STRING COMMENT 'Route destination state.',
  load_month DATE COMMENT 'Calendar month of load booking (truncated to month start).',
  total_loads BIGINT COMMENT 'Count of loads on this route in this month.',
  total_revenue DOUBLE COMMENT 'Sum of load revenue plus fuel surcharge and accessorial charges.',
  total_miles DOUBLE COMMENT 'Sum of actual trip distance miles.',
  total_fuel_cost_estimate DOUBLE COMMENT 'Fuel gallons used times a $3.80/gal reference price — directional cost estimate, not actual purchase cost.',
  revenue_per_mile DOUBLE COMMENT 'total_revenue / total_miles.'
)
CLUSTER BY (route_id)
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
COMMENT 'Revenue, miles, and estimated fuel cost by route and month. Answers "which lanes are most/least profitable" and "what is revenue per mile by route".'
AS SELECT
  route_id,
  ANY_VALUE(origin_city) AS origin_city,
  ANY_VALUE(origin_state) AS origin_state,
  ANY_VALUE(destination_city) AS destination_city,
  ANY_VALUE(destination_state) AS destination_state,
  CAST(DATE_TRUNC('MONTH', load_date) AS DATE) AS load_month,
  COUNT(DISTINCT load_id) AS total_loads,
  SUM(revenue + fuel_surcharge + accessorial_charges) AS total_revenue,
  SUM(actual_distance_miles) AS total_miles,
  SUM(fuel_gallons_used) * 3.80 AS total_fuel_cost_estimate,
  SUM(revenue + fuel_surcharge + accessorial_charges) / NULLIF(SUM(actual_distance_miles), 0) AS revenue_per_mile
FROM fleet_pulse.silver.trip_events
GROUP BY route_id, DATE_TRUNC('MONTH', load_date);

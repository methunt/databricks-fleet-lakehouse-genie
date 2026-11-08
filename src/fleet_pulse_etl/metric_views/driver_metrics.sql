CREATE OR REPLACE VIEW fleet_pulse.gold.driver_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: fleet_pulse.silver.trip_events
joins:
  - name: dim_driver
    source: fleet_pulse.bronze.drivers
    'on': source.driver_id = dim_driver.driver_id
comment: "Governed per-driver KPIs, derived entirely from trip facts so they reconcile with route and fleet numbers. Replaces the dataset's driver_monthly_metrics table, which disagrees with the trip facts by ~14% on revenue and ~34% on on-time rate."
dimensions:
  - name: Driver
    expr: "COALESCE(CONCAT(dim_driver.first_name, ' ', dim_driver.last_name), 'Unassigned')"
    comment: "Driver full name, or 'Unassigned' for the 1,714 trips in the source data with no driver assigned."
    display_name: "Driver"
  - name: Driver ID
    expr: source.driver_id
    comment: "Stable driver identifier, for joining to other views."
    display_name: "Driver ID"
  - name: Month
    expr: "DATE_TRUNC('MONTH', source.dispatch_date)"
    comment: "Calendar month of trip dispatch, truncated to the 1st."
    display_name: "Month"
  - name: Home Terminal
    expr: dim_driver.home_terminal
    comment: "Driver's assigned home terminal."
    display_name: "Home Terminal"
measures:
  - name: Trips Completed
    expr: COUNT(1)
    comment: "Number of trips completed."
    display_name: "Trips Completed"
  - name: Total Miles
    expr: SUM(source.actual_distance_miles)
    comment: "Total miles driven, in miles."
    display_name: "Total Miles"
  - name: Total Revenue
    expr: SUM(source.revenue + source.fuel_surcharge + source.accessorial_charges)
    comment: "Total revenue in USD, including fuel surcharge and accessorial charges."
    display_name: "Total Revenue"
  - name: Revenue Per Trip
    expr: "MEASURE(`Total Revenue`) / MEASURE(`Trips Completed`)"
    comment: "Average revenue per trip, in USD."
    display_name: "Revenue per Trip"
  - name: Total Fuel Gallons
    expr: SUM(source.fuel_gallons_used)
    comment: "Total fuel gallons consumed."
    display_name: "Total Fuel Used"
  - name: Average MPG
    expr: "MEASURE(`Total Miles`) / MEASURE(`Total Fuel Gallons`)"
    comment: "Miles per gallon computed from summed miles and summed gallons — a true fuel-efficiency ratio, not an average of averages."
    display_name: "Average Fuel Efficiency"
    synonyms: ["fuel efficiency", "MPG"]
  - name: Deliveries Logged
    expr: COUNT(1) FILTER (WHERE source.scheduled_datetime IS NOT NULL)
    comment: "Trips that have a recorded delivery event — the denominator for on-time rate."
    display_name: "Deliveries Logged"
  - name: On Time Deliveries
    expr: COUNT(1) FILTER (WHERE source.on_time_flag = true)
    comment: "Deliveries that arrived on or before the scheduled time."
    display_name: "On-Time Deliveries"
  - name: On Time Rate
    expr: "MEASURE(`On Time Deliveries`) / MEASURE(`Deliveries Logged`)"
    comment: "Fraction of logged deliveries that were on time."
    display_name: "On-Time Rate"
    synonyms: ["on-time percentage", "on-time performance"]
  - name: Average Idle Hours
    expr: AVG(source.idle_time_hours)
    comment: "Average idle hours per trip."
    display_name: "Average Idle Hours"
$$;

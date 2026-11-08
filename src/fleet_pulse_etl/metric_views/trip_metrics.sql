CREATE OR REPLACE VIEW fleet_pulse.gold.trip_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: fleet_pulse.silver.trip_events
comment: "Governed trip-level KPIs: on-time delivery, route profitability, and fuel efficiency, all derived from the same trip-grain fact so ratios re-aggregate correctly at any dimension (customer, route, month)."
dimensions:
  - name: Trip Date
    expr: dispatch_date
    comment: "Date the trip was dispatched."
    display_name: "Trip Date"
  - name: Trip Month
    expr: "DATE_TRUNC('MONTH', dispatch_date)"
    comment: "Calendar month the trip was dispatched, truncated to the 1st."
    display_name: "Trip Month"
  - name: Customer Name
    expr: customer_name
    comment: "Customer the load was booked for."
    display_name: "Customer"
    synonyms: ["client", "account"]
  - name: Route
    expr: route_id
    comment: "Lane identifier (origin-destination pair)."
    display_name: "Route"
    synonyms: ["lane"]
  - name: Origin City
    expr: origin_city
    comment: "Route origin city."
    display_name: "Origin"
  - name: Destination City
    expr: destination_city
    comment: "Route destination city."
    display_name: "Destination"
measures:
  - name: Total Trips
    expr: COUNT(1)
    comment: "Count of trips in this group."
    display_name: "Total Trips"
  - name: On Time Deliveries
    expr: COUNT(1) FILTER (WHERE on_time_flag = true)
    comment: "Count of deliveries that arrived on or before the scheduled time."
    display_name: "On-Time Deliveries"
  - name: Deliveries Logged
    expr: COUNT(1) FILTER (WHERE scheduled_datetime IS NOT NULL)
    comment: "Trips with a recorded delivery event — the denominator for on-time rate. Trips without one are excluded, not counted as late."
    display_name: "Deliveries Logged"
  - name: On Time Rate
    expr: "MEASURE(`On Time Deliveries`) / MEASURE(`Deliveries Logged`)"
    comment: "Fraction of logged deliveries that were on time."
    display_name: "On-Time Rate"
    synonyms: ["on-time percentage", "on-time performance"]
  - name: Avg Detention Minutes
    expr: AVG(detention_minutes)
    comment: "Average minutes trucks waited at facilities beyond scheduled service."
    display_name: "Average Detention"
    synonyms: ["wait time", "detention time"]
  - name: Total Revenue
    expr: SUM(revenue + fuel_surcharge + accessorial_charges)
    comment: "Total revenue in USD, including fuel surcharge and accessorial charges."
    display_name: "Total Revenue"
  - name: Total Miles
    expr: SUM(actual_distance_miles)
    comment: "Total miles driven, in miles."
    display_name: "Total Miles"
  - name: Revenue Per Mile
    expr: "MEASURE(`Total Revenue`) / MEASURE(`Total Miles`)"
    comment: "Revenue in USD generated per mile driven — the primary profitability indicator by route."
    display_name: "Revenue per Mile"
    synonyms: ["profitability", "rate per mile"]
  - name: Total Fuel Gallons
    expr: SUM(fuel_gallons_used)
    comment: "Total fuel gallons consumed."
    display_name: "Total Fuel Used"
  - name: Average MPG
    expr: "MEASURE(`Total Miles`) / MEASURE(`Total Fuel Gallons`)"
    comment: "Miles per gallon computed from summed miles and summed gallons — a true fuel-efficiency ratio, not an average of averages."
    display_name: "Average Fuel Efficiency"
    synonyms: ["fuel efficiency", "MPG"]
  - name: Total Fuel Cost Estimate
    expr: "MEASURE(`Total Fuel Gallons`) * 3.80"
    comment: "Directional fuel cost estimate in USD using a fixed $3.80/gal reference price — not actual purchase cost from fuel_purchases."
    display_name: "Estimated Fuel Cost"
$$;

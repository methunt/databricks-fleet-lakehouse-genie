CREATE OR REPLACE VIEW fleet_pulse.gold.truck_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: fleet_pulse.silver.trip_events
joins:
  - name: dim_truck
    source: fleet_pulse.bronze.trucks
    'on': source.truck_id = dim_truck.truck_id
comment: "Governed per-truck performance KPIs (trips, miles, revenue, fuel efficiency), derived from trip facts so they reconcile with route and driver numbers. Maintenance cost and downtime live in truck_maintenance_metrics — joining a maintenance fact at trip grain would fan out and double-count trips."
dimensions:
  - name: Truck
    expr: dim_truck.unit_number
    comment: "Human-readable truck unit number."
    display_name: "Truck"
  - name: Truck ID
    expr: source.truck_id
    comment: "Stable truck identifier, for joining to truck_maintenance_metrics."
    display_name: "Truck ID"
  - name: Month
    expr: "DATE_TRUNC('MONTH', source.dispatch_date)"
    comment: "Calendar month of trip dispatch, truncated to the 1st."
    display_name: "Month"
  - name: Home Terminal
    expr: dim_truck.home_terminal
    comment: "Truck's assigned home terminal."
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
  - name: Revenue Per Mile
    expr: "MEASURE(`Total Revenue`) / MEASURE(`Total Miles`)"
    comment: "Revenue in USD generated per mile driven."
    display_name: "Revenue per Mile"
    synonyms: ["profitability", "rate per mile"]
  - name: Total Fuel Gallons
    expr: SUM(source.fuel_gallons_used)
    comment: "Total fuel gallons consumed."
    display_name: "Total Fuel Used"
  - name: Average MPG
    expr: "MEASURE(`Total Miles`) / MEASURE(`Total Fuel Gallons`)"
    comment: "Miles per gallon computed from summed miles and summed gallons — a true fuel-efficiency ratio, not an average of averages."
    display_name: "Average Fuel Efficiency"
    synonyms: ["fuel efficiency", "MPG"]
  - name: Average Idle Hours
    expr: AVG(source.idle_time_hours)
    comment: "Average idle hours per trip."
    display_name: "Average Idle Hours"
$$;

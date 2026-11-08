CREATE OR REPLACE VIEW fleet_pulse.gold.truck_maintenance_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: fleet_pulse.bronze.maintenance_records
joins:
  - name: dim_truck
    source: fleet_pulse.bronze.trucks
    'on': source.truck_id = dim_truck.truck_id
comment: "Governed per-truck maintenance KPIs: service events, cost, and downtime. Single source is the maintenance fact (one row per service event), kept separate from truck_metrics so joining maintenance to trips cannot fan out and double-count trip figures."
dimensions:
  - name: Truck
    expr: dim_truck.unit_number
    comment: "Human-readable truck unit number."
    display_name: "Truck"
  - name: Truck ID
    expr: source.truck_id
    comment: "Stable truck identifier, for joining to truck_metrics."
    display_name: "Truck ID"
  - name: Month
    expr: "DATE_TRUNC('MONTH', source.maintenance_date)"
    comment: "Calendar month of the maintenance event, truncated to the 1st."
    display_name: "Month"
  - name: Maintenance Type
    expr: source.maintenance_type
    comment: "Category of service performed."
    display_name: "Maintenance Type"
measures:
  - name: Maintenance Events
    expr: COUNT(1)
    comment: "Number of service events."
    display_name: "Maintenance Events"
  - name: Maintenance Cost
    expr: SUM(source.total_cost)
    comment: "Total maintenance spend, in USD."
    display_name: "Maintenance Cost"
  - name: Average Cost Per Event
    expr: "MEASURE(`Maintenance Cost`) / MEASURE(`Maintenance Events`)"
    comment: "Average cost per service event, in USD."
    display_name: "Average Cost per Event"
  - name: Downtime Hours
    expr: SUM(source.downtime_hours)
    comment: "Total hours the truck was out of service for maintenance."
    display_name: "Downtime Hours"
  - name: Average Downtime Per Event
    expr: "MEASURE(`Downtime Hours`) / MEASURE(`Maintenance Events`)"
    comment: "Average hours out of service per service event."
    display_name: "Average Downtime per Event"
$$;

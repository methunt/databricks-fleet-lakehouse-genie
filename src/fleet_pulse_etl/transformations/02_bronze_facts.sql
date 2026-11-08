-- Bronze facts: Auto Loader over yearly CSVs (3 files per table = 3 ingest
-- batches). Liquid clustering keyed to each table's expected Genie filter
-- column so downstream reads skip-scan instead of full-scan. schemaHints
-- pin types explicitly so the 3 yearly batches never drift; rescue column
-- quarantines malformed rows instead of failing the whole batch.

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.loads
CLUSTER BY (load_date)
COMMENT 'Shipment bookings: customer, route, weight, revenue, booking type. One row per load_id. Clustered by load_date for time-range queries.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/loads/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  schemaHints => 'load_id STRING, customer_id STRING, route_id STRING, load_date DATE, weight_lbs DOUBLE, pieces INT, revenue DOUBLE, fuel_surcharge DOUBLE, accessorial_charges DOUBLE',
  rescuedDataColumn => '_rescued_data'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.trips
CLUSTER BY (dispatch_date)
COMMENT 'Executed trips: driver, truck, trailer, actual distance/duration/fuel/MPG. One row per trip_id. Clustered by dispatch_date.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/trips/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  schemaHints => 'trip_id STRING, load_id STRING, driver_id STRING, truck_id STRING, trailer_id STRING, dispatch_date DATE, actual_distance_miles DOUBLE, actual_duration_hours DOUBLE, fuel_gallons_used DOUBLE, average_mpg DOUBLE, idle_time_hours DOUBLE',
  rescuedDataColumn => '_rescued_data'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.delivery_events
CLUSTER BY (scheduled_datetime)
COMMENT 'Pickup/delivery timestamps, detention minutes, on-time flag, facility. One row per event_id. Clustered by scheduled_datetime.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/delivery_events/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  schemaHints => 'event_id STRING, load_id STRING, trip_id STRING, facility_id STRING, scheduled_datetime TIMESTAMP, actual_datetime TIMESTAMP, detention_minutes DOUBLE',
  rescuedDataColumn => '_rescued_data'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.fuel_purchases
CLUSTER BY (purchase_date)
COMMENT 'Fuel transactions: trip, truck, driver, gallons, price per gallon, total cost. One row per fuel_purchase_id.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/fuel_purchases/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  schemaHints => 'fuel_purchase_id STRING, trip_id STRING, truck_id STRING, driver_id STRING, purchase_date TIMESTAMP, gallons DOUBLE, price_per_gallon DOUBLE, total_cost DOUBLE',
  rescuedDataColumn => '_rescued_data'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.maintenance_records
CLUSTER BY (truck_id)
COMMENT 'Service history: truck, maintenance type, odometer, labor/parts cost, downtime hours. One row per maintenance_id. Clustered by truck_id for per-asset lookups.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/maintenance_records/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  schemaHints => 'maintenance_id STRING, truck_id STRING, maintenance_date DATE, odometer_reading DOUBLE, labor_hours DOUBLE, labor_cost DOUBLE, parts_cost DOUBLE, total_cost DOUBLE, downtime_hours DOUBLE',
  rescuedDataColumn => '_rescued_data'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.safety_incidents
CLUSTER BY (driver_id)
COMMENT 'Accidents and violations: trip, truck, driver, at-fault/injury flags, damage/claim costs. One row per incident_id. Clustered by driver_id.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/safety_incidents/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  schemaHints => 'incident_id STRING, trip_id STRING, truck_id STRING, driver_id STRING, incident_date DATE, vehicle_damage_cost DOUBLE, cargo_damage_cost DOUBLE, claim_amount DOUBLE',
  rescuedDataColumn => '_rescued_data'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.driver_monthly_metrics
CLUSTER BY (driver_id)
COMMENT 'Monthly per-driver performance summary: trips, miles, revenue, MPG, on-time rate, idle hours. Composite key driver_id+month.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/driver_monthly_metrics/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  schemaHints => 'driver_id STRING, month DATE, total_miles DOUBLE, total_revenue DOUBLE, average_mpg DOUBLE, total_fuel_gallons DOUBLE, on_time_delivery_rate DOUBLE, average_idle_hours DOUBLE',
  rescuedDataColumn => '_rescued_data'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.truck_utilization_metrics
CLUSTER BY (truck_id)
COMMENT 'Monthly per-truck utilization summary: trips, miles, revenue, MPG, maintenance events/cost, downtime, utilization rate. Composite key truck_id+month.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/truck_utilization_metrics/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  schemaHints => 'truck_id STRING, month DATE, total_miles DOUBLE, total_revenue DOUBLE, average_mpg DOUBLE, maintenance_cost DOUBLE, downtime_hours DOUBLE, utilization_rate DOUBLE',
  rescuedDataColumn => '_rescued_data'
);

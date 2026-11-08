-- Bronze dimensions: small, static reference data loaded once via Auto Loader.
-- Each is a streaming table so the whole pipeline uses one ingestion mechanism,
-- but no clustering/optimizeWrite — single-file, single-batch, no layout to tune.
-- read_files requires a directory; pathGlobFilter isolates each table's file
-- inside the shared dimensions/ folder.

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.customers
COMMENT 'Customer accounts: contract type, credit terms, primary freight type, revenue potential. One row per customer_id.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/dimensions/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  pathGlobFilter => 'customers.csv',
  schemaHints => 'customer_id STRING, contract_start_date DATE, annual_revenue_potential DOUBLE'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.drivers
COMMENT 'Driver roster: hire/termination dates, license info, CDL class, years of experience. One row per driver_id.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/dimensions/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  pathGlobFilter => 'drivers.csv',
  schemaHints => 'driver_id STRING, hire_date DATE, termination_date DATE, date_of_birth DATE, years_experience INT'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.trucks
COMMENT 'Fleet truck inventory: make, model year, acquisition info, fuel type, tank capacity, status. One row per truck_id.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/dimensions/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  pathGlobFilter => 'trucks.csv',
  schemaHints => 'truck_id STRING, unit_number STRING, model_year INT, acquisition_date DATE, acquisition_mileage DOUBLE, tank_capacity_gallons DOUBLE'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.trailers
COMMENT 'Trailer inventory: type, length, model year, acquisition date, status, current location. One row per trailer_id.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/dimensions/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  pathGlobFilter => 'trailers.csv',
  schemaHints => 'trailer_id STRING, trailer_number STRING, length_feet DOUBLE, model_year INT, acquisition_date DATE'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.routes
COMMENT 'Origin-destination lanes: distance, base rate per mile, fuel surcharge rate, typical transit days. One row per route_id.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/dimensions/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  pathGlobFilter => 'routes.csv',
  schemaHints => 'route_id STRING, typical_distance_miles DOUBLE, base_rate_per_mile DOUBLE, fuel_surcharge_rate DOUBLE, typical_transit_days INT'
);

CREATE OR REFRESH STREAMING TABLE fleet_pulse.bronze.facilities
COMMENT 'Terminal and warehouse locations: type, geocoordinates, dock doors, operating hours. One row per facility_id.'
AS SELECT * FROM STREAM read_files(
  '/Volumes/fleet_pulse/bronze/raw_events/dimensions/',
  format => 'csv',
  header => true,
  inferColumnTypes => true,
  pathGlobFilter => 'facilities.csv',
  schemaHints => 'facility_id STRING, latitude DOUBLE, longitude DOUBLE, dock_doors INT'
);

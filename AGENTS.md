# AGENTS.md

Orientation for a new session. Read this first, then `README.md` for the public write-up.

## What this repo is

**Fleet Pulse** is a portfolio project: a Databricks medallion lakehouse over three years (2022–2024) of trucking
operations from the Kaggle dataset `yogape/logistics-operations-database` (14 tables, ~85K trips, synthetic).
It is built with Lakeflow Declarative Pipelines and a Databricks Asset Bundle, and ends in four governed
metric views, a Genie agent and an AI/BI dashboard.

The repo holds the **code and definitions**. It does **not** hold any workspace host, profile, or resource ID.
Those were removed on purpose and must not be re-added (see "Identifiers").

## Layout

| Path | What it is |
|---|---|
| `databricks.yml` | Bundle root. One variable (`catalog`), one target (`dev`, development mode). **No host** — it comes from the CLI profile. |
| `resources/fleet_pulse_etl.pipeline.yml` | The Lakeflow pipeline resource: serverless, catalog `fleet_pulse`, default schema `bronze`. |
| `src/fleet_pulse_etl/transformations/` | Pipeline SQL, numbered by layer: `01`–`02` bronze, `03` silver, `04`–`08` gold. |
| `src/fleet_pulse_etl/metric_views/` | Four metric views (YAML inside `CREATE VIEW ... WITH METRICS`). **Not part of the pipeline** — deployed separately. |
| `genie/fleet_pulse_genie.json` | Genie `serialized_space`: 4 sources, 5 sample questions, 6 example SQLs, 1 instruction block, 7 benchmarks. |
| `genie/update_payload.json` | A wrapper (`{"serialized_space": "<string>"}`) generated from the file above for `genie update-space`. Derived; regenerate rather than hand-edit. |
| `dashboards/fleet_pulse_dashboard.json` | AI/BI dashboard definition. `uiSettings.genieSpace.overrideId` is the placeholder `<GENIE_SPACE_ID>`. |
| `loader/build_annual_csvs.py` | Splits the Kaggle CSVs into 30 yearly files (24 fact, 6 dimension). Output is byte-identical on re-run. |
| `scripts/build_assets.py` | Generates the README's SVGs from `scripts/readme-assets.json` + `scripts/readme-facts.json` (light + dark). Output: `assets/`. |
| `scripts/build_showcase.py` | Generates `showcase.html` from `scripts/showcase.template.html` + `scripts/showcase-data.json`. `--refresh` re-queries the warehouse. |
| `showcase.html` | Generated single-file summary page. Edit the template, not this file. |
| `pyproject.toml` | Written by the Databricks VS Code extension (`databricks-connect`). Nothing in the repo imports it. |

Local only, git-ignored, **may not exist** in a fresh clone: `plan.md`, `status.md`, `.databricks/`, `annual_csvs/`
(58 MB, regenerate with the loader), `.venv/`.

## Architecture in one pass

```
30 yearly CSVs -> UC volume -> 14 bronze streaming tables (Auto Loader)
               -> 1 silver streaming table (trip_events, joined to 4 dimensions)
               -> 5 gold tables (3 materialized views + 2 streaming tables)
silver.trip_events (+ bronze.maintenance_records) -> 4 metric views -> Genie agent + dashboard
```

Rules that are easy to break:

- **Streaming table vs materialized view.** A streaming table is append-only; a `GROUP BY` in one appends partial
  groups per batch. Aggregations must be materialized views.
- **`CLUSTER BY` and `PARTITIONED BY` are mutually exclusive** in Lakeflow. This project uses `CLUSTER BY` only.
- **`read_files()` takes a directory.** The six dimension files share one folder, so each bronze dimension table
  narrows with `pathGlobFilter`.
- **`DATE_TRUNC` returns TIMESTAMP.** Gold month columns are `CAST(DATE_TRUNC(...) AS DATE)`.
- **Metric views read the trip fact, never the source's monthly tables.** `bronze.driver_monthly_metrics` and
  `bronze.truck_utilization_metrics` disagree with the trip rows (about 13.8% of revenue), so no metric view uses them.
- **Ratios are `MEASURE(a) / MEASURE(b)` over summed values**, never an average of averages (MPG is
  Σ miles ÷ Σ gallons = 6.4477, not the 6.5015 you get from averaging per-trip MPG).
- **Cross-view joins must use the entity grain.** `truck_metrics.Month` is the dispatch month and
  `truck_maintenance_metrics.Month` is the service month. Join the two on `Truck ID` only; joining on
  `Truck ID + Month` silently drops about half the revenue. The Genie instructions and an example SQL encode this.
- **`gold.driver_scorecard` and `gold.fleet_utilization` are orphans.** Nothing consumes them and they still read the
  unreconciled source tables. They are candidates for deletion; do not build on them.

## Verified numbers

Use these to sanity-check any rebuild. They came from live queries, not estimates.

| Metric | Value |
|---|---|
| Revenue / trips | $298,621,429 / 85,410 |
| On-time rate | 33.27% (85,333 logged deliveries) |
| Fleet MPG | 6.4477 |
| Trips with an empty `driver_id` | 1,714 (labelled `Unassigned`) |
| Row counts | bronze loads/trips 85,410 each; delivery_events 170,743; silver trip_events 85,410; gold on_time_delivery 77,202 |

## Identifiers — where they are and how to find them

This repo contains **no** workspace host, profile name, warehouse ID, pipeline ID, Genie space ID or dashboard ID.
Do not add them to any tracked file. They live in:

- **Host and auth:** a CLI profile in `~/.databrickscfg`. Always pass `--profile <name>`. Read the section names to
  find the right one, not the contents (the file can hold tokens).
- **Local-only notes:** `status.md` (if present) lists the IDs of the deployed copy.
- **Discover them live:** `databricks warehouses list`, `databricks pipelines list-pipelines`,
  `databricks genie list-spaces`, `databricks lakeview list`.

## Commands

All take `--profile <profile>`. Run from the repo root.

```bash
python loader/build_annual_csvs.py                      # 30 yearly CSVs -> ./annual_csvs (needs kagglehub)

databricks bundle validate --profile <profile>
databricks bundle deploy -t dev --profile <profile>
databricks bundle run fleet_pulse_etl -t dev --profile <profile>
databricks pipelines start-update <PIPELINE_ID> --full-refresh --profile <profile>

# Metric views: use the Statement Execution API, NOT `aitools tools query`
jq -Rs --arg wh "$WAREHOUSE_ID" '{warehouse_id:$wh, statement:., wait_timeout:"30s"}' <file>.sql > /tmp/p.json
databricks api post /api/2.0/sql/statements/ --json @/tmp/p.json --profile <profile>

python scripts/build_assets.py                          # regenerate assets/*.svg
python scripts/build_showcase.py                        # rebuild showcase.html from the data file
DATABRICKS_PROFILE=<profile> python scripts/build_showcase.py --refresh   # re-query first
```

Genie and dashboard deploys are in README Part 6. The dashboard JSON needs `<GENIE_SPACE_ID>` replaced with a real
space ID before `lakeview create` or `update`; `lakeview update` must also re-pass `--dataset-catalog` and
`--dataset-schema`, then `lakeview publish` again.

## Gotchas that have already cost time

- **`dbfs:` prefix.** `databricks fs cp` to a UC Volume without `dbfs:` writes a path Spark cannot see. Create each
  directory with `fs mkdirs` first.
- **`COMPLETED` is not proof.** A pipeline update succeeded while `gold.on_time_delivery` held 0 rows (a string
  compare on `'delivery'` vs data saying `'Delivery'`). Count rows after every refresh.
- **Streaming-table state.** Fixing a join in a streaming table needs a full refresh of that table; redeploying
  alone keeps the old rows.
- **`aitools tools query` flattens indentation** inside `$$...$$`, which breaks metric-view YAML. Use the API.
- **Free Edition limits.** The dashboard needs workspace sign-in and cannot be shared by link; serverless blocks
  most outbound traffic. That is why data arrives as uploaded files and why the README has no live dashboard link.
- **Genie follows example SQL better than prose.** A written rule to exclude `Unassigned` was ignored; the same
  rule as an example query worked.
- **CRLF warnings** from git on Windows are cosmetic.

## Conventions

- **Generated files:** `assets/*.svg` and `showcase.html` are build outputs. Change `scripts/readme-assets.json`,
  `scripts/readme-facts.json` or `scripts/showcase.template.html`, then rebuild. Template tokens are `{{name}}`; an
  unknown token fails the build instead of rendering blank.
- **Figures in prose** (README, showcase) should come from queried values. If you change a number in one place,
  check the other.
- **First person** in showcase and README copy ("I stopped it", "What I learned"), not "we".
- **Do not claim what was not observed.** Earlier drafts invented durations and savings that had to be removed.
- **Secrets and identifiers:** never commit a host, token, profile name or resource ID. Before committing, scan the
  index (`git grep --cached`) for them.

## State

Complete and verified in the workspace it was built in. The pipeline, four metric views, Genie space and dashboard
are all deployed there. Known open items: the two orphan gold tables above; `docs/` is empty and still needs
three screenshots (dashboard, a Genie answer showing `MEASURE()` SQL, the pipeline graph); the seven Genie
benchmarks exist but have not been run through the native evaluation.

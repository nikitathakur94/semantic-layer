# distribution-semantics-lab

## Quickstart (macOS)

Install Python 3.12 if needed (`brew install python@3.12`), then run from this folder:

```bash
make setup
cp .env.example .env
# Edit .env: set SEC_USER_AGENT to your name/organization and real contact email.
make refresh
make test
make app
```

Open [localhost:8502](http://localhost:8502). Stop with Ctrl-C. Allow roughly 1 GB
free disk space plus the Python environment. The first refresh downloads a ~398 MB
SEC archive; later refreshes reuse it. Choose a snapshot date, flow months, funds,
registrants or the name-matched cohort in the sidebar. Inspect definitions and SQL
at the bottom of the dashboard.

## Commands

| Command | Use |
| --- | --- |
| `make setup` | Create the Python 3.12 environment, install locked packages, prove a real local `mf query` returns 42 |
| `make refresh` | Cached SEC ingestion, dbt build/tests, source/model audit |
| `make refresh ZIP="/absolute/path/2025q4_nport.zip"` | Import a manually downloaded official ZIP |
| `make test` | dbt tests, Python tests, five golden questions on real + fixture data, Streamlit execution checks |
| `make app` | Start the dashboard on localhost:8502 |
| `make parse` | Reparse changed semantic YAML and regenerate the metric catalog |
| `make smoke` | Repeat the isolated MetricFlow compatibility gate |

For a direct CLI query:

```bash
source .venv/bin/activate
export DBT_PROFILES_DIR="$PWD"
mf query --metrics reported_net_assets,fund_count \
  --start-time 2025-09-30 --end-time 2025-09-30
mf query --metrics gross_sales,redemptions_to_sales_ratio \
  --group-by metric_time__month --start-time 2025-07-01 --end-time 2025-10-31
mf query --metrics reported_net_assets --explain
```

## Folder map / 2–3 hour walkthrough

| Path | Open or run |
| --- | --- |
| `scripts/smoke.py`, `requirements.in`, `requirements.txt` | 15 min: setup and CLI gate |
| `scripts/ingest.py`, `data/ingestion_manifest.json` | 25 min: refresh and inspect provenance |
| `models/staging/`, `models/marts/` | 35 min: follow the SQL in dependency order |
| `models/semantic.yml`, [metric catalog](docs/metrics.md) | 25 min: inspect the seven definitions |
| `lab/query.py`, `app.py` | 25 min: follow a dashboard query |
| `tests/reference/`, `tests/fixture.py`, `scripts/golden.py` | 25 min: run and inspect golden checks |
| [Architecture](docs/architecture.md), [modeling decisions](docs/semantics.md) | Reference while reading |
| [Verification record](docs/verification.md) | Review results from the completed local run |
| `data/`, `target/`, `logs/`, `.venv/`, `.env` | Generated/ignored local files |

## Troubleshooting

- **Python missing:** `make setup PYTHON=/opt/homebrew/bin/python3.12` (Intel Homebrew
  normally uses `/usr/local/bin/python3.12`). Python 3.13 is not this lab's runtime.
- **SEC 403/429 or network failure:** wait, check the identifying User-Agent, then
  download **2025 Q4** from the [official SEC page](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets)
  in a browser. Run the manual-ZIP command above. Never rename a different quarter
  as Q4. Do not disable TLS verification or work around SEC access restrictions.
- **Need a fresh archive:** move `data/cache/2025q4_nport.zip` and its `.json` sidecar
  elsewhere, then `make refresh`. Normal refresh deliberately uses the cache.
- **DuckDB lock error:** stop the app and any DuckDB shell while refreshing; restart
  after the build. Avoid running refresh and tests simultaneously.
- **Definitions changed / stale manifest:** `make parse`, then rerun Streamlit.
  The cache automatically changes with the manifest or database. To reclaim cache
  disk space, remove `data/query_cache` while the app is stopped.
- **No cards / dashes:** choose another reporting date or broaden the filters.
  Review missing-data coverage; nulls and zero-denominator ratios are not zero.
- **CLI suggests upgrading:** retain the lockfile versions; `make setup` verifies
  the tested stack. Upgrade only with a new successful smoke and golden run.
- **Port 8502 busy:** stop the existing app or use
  `make app PORT=8503`.

## Exercise: change a metric and watch the dashboard change

1. Record the current net-flow card for fixed filters. Open `models/semantic.yml`
   and locate `net_flows_excluding_reinvestments` under `metrics:`.
2. Temporarily change its `expr` to `gross_sales - redemptions + reinvestments`,
   and add `- name: reinvestments` to that metric's `type_params.metrics` list.
   Change its label to `Exercise: net flows including reinvestments` and its
   description to match. Keep the identifier so the existing card picks it up.
3. Run `make parse`, then rerun the dashboard. The card now includes reinvestments;
   use **Inspect metric → Show generated SQL** to verify the changed expression.
   No Python dashboard formula needs editing. The golden baseline intentionally
   expects the original definition and should fail while this exercise is active.
4. Restore the expression, dependencies, label and description, run `make parse`,
   then `make test` to return to the checked baseline.

## Publishing

The configured remote is `https://github.com/nikitathakur94/semantic-layer.git`.
If authentication is unavailable on a new machine:

```bash
git remote -v
gh auth login --hostname github.com --git-protocol https
gh auth setup-git
git push -u origin main
```

Use `git status --short` before publishing; data, environments and `.env` are ignored.
